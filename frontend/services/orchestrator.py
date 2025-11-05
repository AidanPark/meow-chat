"""
Meow Chat 오케스트레이터 (LangGraph 기반)
=======================================================================

이 모듈은 MultiServerMCPClient로 노출된 여러 MCP 서버/로컬 도구를
"상태(State)를 가진 그래프"로 오케스트레이션합니다. 현재 두 가지 흐름을 제공합니다.

1) 규칙 기반 스켈레톤(Math/Weather)
    - router → (math | weather) → compose 의 단순 파이프라인
    - 목적: "작업 라우팅 → 도구 호출 → 결과 합성"의 최소 패턴 예시
    - task="math" 일 때: add/multiply/… 같은 MathUtilityServer 도구 호출
    - task="weather" 일 때: get_weather/get_forecast/… 같은 WeatherAPIServer 도구 호출

2) ReAct RAG 루프(Reason-Act-Observe)
    - plan(한 단계 Action 설계) → execute(도구 호출) → self-eval(계속/종료 판단) → compose
    - 각 반복에서 단일 스텝(action={tool,args,save_as})만 계획하고 실행하여, 관찰 결과를 바탕으로 다음 스텝을 결정합니다.
    - 안전장치: 허용 도구 화이트리스트, 반복 횟수 제한, 오류 누적/관찰(툴 사용 기록)

핵심 개념
-----------
- OrchestratorState: 그래프를 흐르는 단일 상태(입력/출력/오류/도구사용/계획/변수 등)
- MCPToolInvoker: MCP 도구를 이름으로 찾아 비동기로 호출하는 래퍼
- 로컬 함수 도구: 프로세스 내 함수형 도구(예: OCR 어댑터)를 MCP와 동일한 인터페이스로 실행
- 노드(Node): 상태를 입력받아 갱신 후 반환하는 (비)동기 함수
- 엣지(Edge): 다음 노드로의 연결. 조건부 엣지로 분기 가능

상태(State) 설계 요약
----------------------
- task: "math" | "weather" (규칙 스켈레톤용)
- inputs/outputs: 각 노드가 읽고/쓰는 I/O 컨테이너
- errors/warnings: 단계별 예외/경고 누적(Compose에서 사용자 메시지로 환원 가능)
- tools_used: {name, args, ok} 리스트로 관찰성 확보(UI tool_history에 반영)
- user_request/plan/vars: ReAct 루프에서 사용되는 요청/단계 계획/변수 컨테이너

운영/확장 포인트
------------------
- 재시도/타임아웃/회로 차단: MCPToolInvoker 또는 로컬 도구 레이어에서 확장
- 병렬 실행/Map 노드: 여러 입력(batch)에 대한 동시 처리(동시성 제한 필수)
- 계획/입력 검증 강화: 타입/범위 검증, 금지 도구/인자 필터, 비용 상한
- 관찰성: 단계별 ms, 호출 횟수, 성공률, 오류 사유 등을 로깅/메트릭으로 적재

주의 사항
----------
- 어떤 도구가 문자열을 반환한다면, 후속 단계에서 파싱/정규화 또는 MCP 서버/로컬 도구에서 구조화(JSON) 반환을 권장합니다.
- 본 파일은 "오케스트레이션" 레이어이며, UI 연결/토글은 frontend/app.py 에서 처리합니다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, TypedDict, Callable, Awaitable
import json as _json
import logging
import os

try:
    # LangGraph 1.0+ API
    from langgraph.graph import StateGraph, END
except Exception as e:  # pragma: no cover - 환경에 따라 예외 메시지 보강
    raise ImportError(
        "LangGraph를 찾을 수 없습니다. backend/requirements.txt에 명시된 버전으로 설치해주세요."
    ) from e


# -----------------------------
# 상태 모델
# -----------------------------

TaskType = Literal["math", "weather"]


class OrchestratorState(TypedDict, total=False):
    task: TaskType
    # 사용자가 전달하는 입력. 예:
    # - math: {operation: "add"|"multiply"|..., a: number, b: number}
    # - weather: {method: "get_weather"|"get_forecast"|..., location: str, days?: int}
    inputs: Dict[str, Any]

    # 노드가 채워 넣는 출력
    outputs: Dict[str, Any]

    # 오류 및 경고 누적
    errors: List[str]
    warnings: List[str]

    # 관찰/추적용 메타데이터
    tools_used: List[Dict[str, Any]]  # {name, args, ok(bool), ms?}
    message: Optional[str]  # 최종 사용자용 메시지

    # 공통/계획 관련 필드(ReAct에서 사용)
    user_request: Optional[str]
    allowed_tools: Optional[List[str]]
    plan: Optional[Dict[str, Any]]
    vars: Dict[str, Any]
    primary_output: Any

    # ReAct RAG용 확장 필드
    react_iteration: int
    react_max_iters: int
    react_history: List[Dict[str, Any]]  # [{step, observation, ok} ...]
    react_finish: Optional[Dict[str, Any]]  # {"use": "var"|"message", "value": str}
    react_should_continue: Optional[bool]


# -----------------------------
# 로깅(오케스트레이터 전략 & 도구 호출)
# -----------------------------
_ORCH_LOGGER = logging.getLogger("meow.frontend.orchestrator")
if not _ORCH_LOGGER.handlers:
    _ORCH_LOGGER.setLevel(logging.INFO)
    _ch = logging.StreamHandler()
    _ch.setLevel(logging.INFO)
    _fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    _ch.setFormatter(_fmt)
    _ORCH_LOGGER.addHandler(_ch)

    # 프론트엔드 로그 디렉터리(frontend/logs/)에 orchestrator.log를 기록합니다.
    try:
        _BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # frontend/
        _LOG_DIR = os.path.join(_BASE_DIR, "logs")
        os.makedirs(_LOG_DIR, exist_ok=True)
        _fh = logging.FileHandler(os.path.join(_LOG_DIR, "orchestrator.log"))
        _fh.setLevel(logging.INFO)
        _fh.setFormatter(_fmt)
        _ORCH_LOGGER.addHandler(_fh)
    except Exception:
        # 파일 핸들러 실패 시 콘솔 로깅만 사용합니다.
        pass

def _preview_data(data: Any, max_len: int = 1200) -> str:
    """로그에 출력하기 위한 안전한 요약 문자열(최대 길이 제한)을 생성합니다."""
    try:
        import json as _json
        if isinstance(data, (dict, list, tuple)):
            try:
                txt = _json.dumps(data, ensure_ascii=False)  # may raise
            except Exception:
                txt = str(data)
        else:
            txt = str(data)
        if len(txt) > max_len:
            return txt[:max_len] + "…"
        return txt
    except Exception:
        try:
            return repr(data)[:max_len]
        except Exception:
            return "<unprintable>"


# -----------------------------
# 로컬 함수 도구 (하이브리드 접근)
# -----------------------------
class SimpleLocalTool:
    """ainvoke(args)->Any 형태의 경량 로컬 함수형 도구."""

    def __init__(self, name: str, description: str, ainvoke: Callable[[Dict[str, Any]], Awaitable[Any]]):
        self.name = name
        self.description = description
        self._ainvoke = ainvoke

    async def ainvoke(self, args: Dict[str, Any]) -> Any:
        return await self._ainvoke(args)


def _build_local_tools(client) -> List[SimpleLocalTool]:
    """현 시점엔 로컬 도구를 제공하지 않습니다(모든 흐름은 MCP 도구로 처리)."""
    return []


# -----------------------------
# MCP 도구 호출 유틸
# -----------------------------

@dataclass
class MCPToolInvoker:
    """MCP 도구 호출을 위한 래퍼.

    - 도구 목록을 지연 조회하고 이름으로 캐싱하여 반복 호출 비용을 줄입니다.
    - fastmcp Tool 인터페이스의 ainvoke(args: dict) 규약을 따릅니다.
    - 재시도/타임아웃/메트릭 수집은 이 레이어에 확장하는 것이 가장 용이합니다.
    """
    client: Any
    _tool_cache: Dict[str, Any] = field(default_factory=dict)

    async def get(self, name: str) -> Any:
        if name in self._tool_cache:
            return self._tool_cache[name]
        tools = await self.client.get_tools()
        for t in tools:
            if getattr(t, "name", None) == name:
                self._tool_cache[name] = t
                return t
        raise KeyError(f"MCP tool not found: {name}")

    async def call(self, name: str, args: Dict[str, Any]) -> Any:
        tool = await self.get(name)
        # fastmcp의 Tool은 비동기 ainvoke를 노출합니다.
        return await tool.ainvoke(args)


# -----------------------------
# 노드 구현
# -----------------------------

def router_node(state: OrchestratorState) -> OrchestratorState:
    """규칙 기반 라우팅 노드.

    - 현재는 단순히 state.task 값을 그대로 사용합니다.
    - 의도 분류가 필요하면 여기서 LLM/규칙을 통해 task를 결정하도록 확장하세요.
    """
    return state

async def math_node(state: OrchestratorState, invoker: MCPToolInvoker) -> OrchestratorState:
    """MathUtilityServer 도구(add/subtract/… 등)를 호출하는 노드.

    입력 예시(state.inputs): {"operation": "add", "a": 1, "b": 2}
    결과는 state.outputs["math"]에 저장되며, 도구 사용 내역은 tools_used에 기록됩니다.
    """
    inputs = state.get("inputs", {})
    op = str(inputs.get("operation", "")).strip().lower()
    record = {"name": None, "args": {}, "ok": False}
    try:
        if op in {"add", "subtract", "multiply", "divide"}:
            a = inputs.get("a")
            b = inputs.get("b")
            if a is None or b is None:
                raise ValueError("'a'와 'b' 인수가 필요합니다")
            record["name"] = op
            record["args"] = {"a": a, "b": b}
            result = await invoker.call(op, {"a": a, "b": b})
        elif op == "convert_units":
            value = inputs.get("value")
            from_unit = inputs.get("from_unit")
            to_unit = inputs.get("to_unit")
            if value is None or not from_unit or not to_unit:
                raise ValueError("value/from_unit/to_unit 인수가 필요합니다")
            record["name"] = "convert_units"
            record["args"] = {"value": value, "from_unit": from_unit, "to_unit": to_unit}
            result = await invoker.call("convert_units", record["args"])  # type: ignore[arg-type]
        elif op == "calculate_percentage":
            part = inputs.get("part")
            total = inputs.get("total")
            if part is None or total is None:
                raise ValueError("part/total 인수가 필요합니다")
            record["name"] = "calculate_percentage"
            record["args"] = {"part": part, "total": total}
            result = await invoker.call("calculate_percentage", record["args"])  # type: ignore[arg-type]
        else:
            raise ValueError(f"지원하지 않는 연산입니다: {op}")

        record["ok"] = True
        out = dict(state.get("outputs") or {})
        out["math"] = result
        state["outputs"] = out
    except Exception as e:
        errs = list(state.get("errors") or [])
        errs.append(f"math_node: {e}")
        state["errors"] = errs
    finally:
        used = list(state.get("tools_used") or [])
        used.append(record)
        state["tools_used"] = used
    return state

async def weather_node(state: OrchestratorState, invoker: MCPToolInvoker) -> OrchestratorState:
    """WeatherAPIServer 도구(get_weather/get_forecast/… 등)를 호출하는 노드.

    입력 예시(state.inputs): {"method": "get_weather", "location": "Seoul"}
    결과는 state.outputs["weather"]에 저장되며, 도구 사용 내역은 tools_used에 기록됩니다.
    """
    inputs = state.get("inputs", {})
    method = str(inputs.get("method", "")).strip()
    record = {"name": None, "args": {}, "ok": False}
    try:
        if method in {"get_weather", "get_air_quality", "get_time_zone", "search_location"}:
            location = inputs.get("location")
            if not location:
                raise ValueError("location 인수가 필요합니다")
            record["name"] = method
            record["args"] = {"location": location}
            result = await invoker.call(method, record["args"])  # type: ignore[arg-type]
        elif method == "get_forecast":
            location = inputs.get("location")
            days = int(inputs.get("days") or 3)
            if not location:
                raise ValueError("location 인수가 필요합니다")
            record["name"] = "get_forecast"
            record["args"] = {"location": location, "days": days}
            result = await invoker.call("get_forecast", record["args"])  # type: ignore[arg-type]
        else:
            raise ValueError(f"지원하지 않는 메서드입니다: {method}")

        record["ok"] = True
        out = dict(state.get("outputs") or {})
        out["weather"] = result
        state["outputs"] = out
    except Exception as e:
        errs = list(state.get("errors") or [])
        errs.append(f"weather_node: {e}")
        state["errors"] = errs
    finally:
        used = list(state.get("tools_used") or [])
        used.append(record)
        state["tools_used"] = used
    return state

def compose_node(state: OrchestratorState) -> OrchestratorState:
    """규칙 기반 결과 합성 노드.

    - 간단한 문자열 결합 방식으로 사용자 메시지를 만듭니다.
    - 운영 단계에서는 LLM 요약/서식화를 붙여 자연스러운 응답으로 교체하는 것을 권장합니다.
    """
    outs = state.get("outputs", {})
    msgs: List[str] = []
    if "math" in outs:
        msgs.append(f"계산 결과: {outs['math']}")
    if "weather" in outs:
        msgs.append(str(outs["weather"]))
    if not msgs and state.get("errors"):
        msgs.append("요청 처리 중 오류가 발생했어요. 인자와 작업을 확인해 주세요.")
    state["message"] = "\n".join(msgs) if msgs else "처리할 결과가 없습니다."
    return state


# -----------------------------
# 그래프 빌더 & 실행 함수
# -----------------------------

def build_math_weather_graph(client) -> Any:
    """Math/Weather 스켈레톤 그래프를 구성해 컴파일합니다.

    흐름: router → (math|weather) → compose → END
    """
    invoker = MCPToolInvoker(client)

    async def _math(state: OrchestratorState) -> OrchestratorState:
        return await math_node(state, invoker)

    async def _weather(state: OrchestratorState) -> OrchestratorState:
        return await weather_node(state, invoker)

    graph = StateGraph(OrchestratorState)
    graph.add_node("router", router_node)
    graph.add_node("math", _math)
    graph.add_node("weather", _weather)
    graph.add_node("compose", compose_node)

    # 기본 시작/종료 흐름: router → (task별) → compose → END
    graph.set_entry_point("router")

    def route_key(state: OrchestratorState) -> str:
        if state.get("task") == "math":
            return "math"
        if state.get("task") == "weather":
            return "weather"
        return "compose"

    graph.add_conditional_edges(
        "router",
        route_key,
        {
            "math": "math",
            "weather": "weather",
            "compose": "compose",
        },
    )
    graph.add_edge("math", "compose")
    graph.add_edge("weather", "compose")
    graph.add_edge("compose", END)

    return graph.compile()

async def run_math_weather(client, task: TaskType, inputs: Dict[str, Any]) -> OrchestratorState:
    """Math/Weather 스켈레톤 그래프의 실행 엔트리포인트.

    task와 inputs를 초기 상태로 설정하고 그래프를 비동기로 실행합니다.
    """
    app = build_math_weather_graph(client)
    init: OrchestratorState = {
        "task": task,
        "inputs": inputs,
        "outputs": {},
        "errors": [],
        "warnings": [],
        "tools_used": [],
        "vars": {},
    }
    result: OrchestratorState = await app.ainvoke(init)
    return result

def _resolve_vars(obj: Any, vars_map: Dict[str, Any]) -> Any:
    # 문자열에서 ${var} 치환. dict/list는 재귀.
    if isinstance(obj, str):
        import re as _re
        def repl(m):
            key = m.group(1)
            return str(vars_map.get(key, m.group(0)))
        return _re.sub(r"\$\{([^}]+)\}", repl, obj)
    if isinstance(obj, list):
        return [_resolve_vars(x, vars_map) for x in obj]
    if isinstance(obj, dict):
        return {k: _resolve_vars(v, vars_map) for k, v in obj.items()}
    return obj

class PlanStep(TypedDict, total=False):
    """ReAct 단계에서 사용하는 경량 Step 타입."""
    tool: str
    args: Dict[str, Any]
    save_as: Optional[str]

class PlanSpec(TypedDict, total=False):
    """ReAct에서 내부적으로 사용하는 간단한 Plan 사양."""
    version: int
    steps: List[PlanStep]
    primary: Optional[str]

    # ----------------------------------------------------------------------------
    # ReAct RAG: Reason-Act-Observe 루프 (단계적 도구 사용 + 자기평가)
    # ----------------------------------------------------------------------------

class ReactDecision(TypedDict, total=False):
    action: Optional[PlanStep]  # {tool, args, save_as}
    finish: Optional[Dict[str, Any]]  # {"use": "var"|"message", "value": str}

async def react_plan_node(state: OrchestratorState, model, client) -> OrchestratorState:
    """다음 한 단계의 Action을 계획하거나 종료를 제안하는 노드.

    입력:
    - user_request, allowed_tools, vars, react_history, react_iteration

    출력:
    - state.plan.steps = [단일 step] 또는 비어있음
    - state.react_finish 설정 가능
    """
    import json as _json

    user_req = (state.get("user_request") or "").strip()
    allowed = state.get("allowed_tools") or []
    vars_map = state.get("vars") or {}
    history = state.get("react_history") or []
    iter_no = int(state.get("react_iteration") or 0)

    # 간단한 도구 목록 추출(이름만)
    try:
        tools = await client.get_tools()
        available = []
        # MCP tools
        for t in tools:
            name = getattr(t, "name", None)
            if not name:
                continue
            if allowed and name not in allowed:
                continue
            desc = getattr(t, "description", None)
            if isinstance(desc, str) and len(desc) > 260:
                desc = desc[:260] + "…"
            available.append({"name": name, "desc": desc or ""})
        # Local tools
        for lt in _build_local_tools(client):
            if allowed and lt.name not in allowed:
                continue
            d = lt.description
            if isinstance(d, str) and len(d) > 260:
                d = d[:260] + "…"
            available.append({"name": lt.name, "desc": d or ""})
    except Exception:
        available = [{"name": n, "desc": ""} for n in (allowed or [])]

    # pinned core facts가 있으면 system 컨텍스트에 함께 제공
    pinned = None
    try:
        pinned = (state.get("vars") or {}).get("pinned_core_facts")
    except Exception:
        pinned = None

    sys_prompt = (
        "당신은 ReAct 스타일 계획자입니다. 지금까지의 관찰과 변수(vars)를 참고하여 다음 한 단계의 action을 설계하거나,\n"
        "충분하면 종료(finish)를 제안하세요. 반드시 JSON만 출력합니다.\n\n"
        "형식:\n"
        "{\n  \"action\": {\"tool\": string, \"args\": object, \"save_as\": string},\n  \"finish\": {\"use\": \"var\"|\"message\", \"value\": string}\n}\n"
        "action과 finish는 동시에 제공하지 말고, 하나만 선택하세요.\n"
    "args에서는 제공된 변수들을 ${변수명} 형태로 참조할 수 있습니다(예: ${user_id}).\n"
        "참고: 직전 단계의 관찰 결과는 vars['_last_observation']로 제공될 수 있습니다. 저장하지 못했더라도 필요 시 ${_last_observation}로 참조하세요.\n"
    )
    # 도구 선택 규칙 힌트(절차 강제가 아닌 선택 원칙)
    sys_prompt += (
        "\n[도구 선택 규칙]\n"
        "- 이미지 첨부가 있고 검사/혈액/수치/결과지 분석이 필요하면, 통합 도구(extract_lab_report)에 이미지 경로(paths)를 직접 전달하세요.\n"
        "- 중간 OCR 단계는 도구 내부에서 처리됩니다. 별도의 OCR 호출은 불필요합니다.\n"
        "- 이미지 경로는 vars.image_paths 배열로 제공됩니다. 이 값을 extract_lab_report(args.paths)로 그대로 사용하세요.\n"
        "  예: {\"paths\": ${image_paths}} 처럼 따옴표 없이 배열 그대로 넘기세요(문자열로 감싸지 마세요).\n"
        "- 실패 시 가능한 정보로 응답하고, 의료 조언은 정보 제공용임을 명시하세요.\n"
    )
    if pinned:
        sys_prompt += f"\n[핵심 사실(요약)]:\n{str(pinned)[:1200]}\n"
    try:
        import json as _json
        vars_preview = _json.dumps({k: vars_map[k] for k in list(vars_map.keys())[:8]}, ensure_ascii=False)
    except Exception:
        vars_preview = str(list(vars_map.keys())[:8])

    # 도구 카탈로그(이름 + 간단 설명) 제공
    tool_lines = []
    try:
        for a in (available or [])[:24]:
            nm = a.get("name")
            ds = a.get("desc") or ""
            if nm:
                line = f"- {nm}: {ds}" if ds else f"- {nm}"
                tool_lines.append(line)
    except Exception:
        pass

    user_prompt = (
        f"요청: {user_req}\n"
        f"허용 도구 목록:\n" + ("\n".join(tool_lines) if tool_lines else "(없음)") + "\n\n"
        f"반복번호: {iter_no}\n"
        f"사용 가능한 변수: {vars_preview}\n"
        f"history 길이: {len(history)}\n"
        "JSON만 출력하세요."
    )

    # Plan 시작 로깅
    try:
        _ORCH_LOGGER.info(
            "[PLAN] iter=%s | request_head=%r | allowed_tools=%s | vars_keys=%s | history_len=%s",
            iter_no,
            (user_req[:140] if isinstance(user_req, str) else user_req),
            [a.get("name") for a in available],
            list((vars_map or {}).keys())[:16],
            len(history),
        )
    except Exception:
        pass

    decision: ReactDecision = {}
    try:
        msg = [{"role": "system", "content": sys_prompt}, {"role": "user", "content": user_prompt}]
        res = await model.ainvoke(msg)
        content = getattr(res, "content", None) or str(res)
        decision = _json.loads(content)
    except Exception as e:
        errs = list(state.get("errors") or [])
        errs.append(f"react_plan_node: {e}")
        state["errors"] = errs
        decision = {}

    # 정규화
    action = decision.get("action") if isinstance(decision, dict) else None
    finish = decision.get("finish") if isinstance(decision, dict) else None
    steps: List[PlanStep] = []
    if action and isinstance(action, dict):
        # allow-list 필터
        if allowed and action.get("tool") not in allowed:
            # 허용되지 않은 도구면 무시하고 finish 유도
            finish = finish or {"use": "message", "value": "허용된 도구 내에서 답변을 마칩니다."}
        else:
            steps = [action]  # 단일 스텝

    # 상태 업데이트
    state["plan"] = {"version": 1, "steps": steps, "primary": (action or {}).get("save_as")}
    if finish:
        state["react_finish"] = finish
    else:
        state["react_finish"] = None

    # Plan 결과 로깅
    try:
        if steps:
            _a = steps[0]
            _ORCH_LOGGER.info(
                "[PLAN->ACTION] iter=%s | tool=%s | args=%s | save_as=%s",
                iter_no,
                _a.get("tool"),
                _preview_data(_a.get("args")),
                _a.get("save_as"),
            )
        elif finish:
            _ORCH_LOGGER.info(
                "[PLAN->FINISH] iter=%s | finish=%s",
                iter_no,
                _preview_data(finish),
            )
        else:
            _ORCH_LOGGER.info("[PLAN] iter=%s | no action/finish produced", iter_no)
    except Exception:
        pass
    return state


async def react_execute_node(state: OrchestratorState, client) -> OrchestratorState:
    """단일 action(step)을 실행하고 관찰(observation)을 기록합니다."""
    invoker = MCPToolInvoker(client)
    vars_map = dict(state.get("vars") or {})
    plan: PlanSpec = (state.get("plan") or {"steps": []})  # type: ignore[assignment]
    steps: List[PlanStep] = plan.get("steps", [])  # type: ignore[assignment]

    observation = None
    ok = False
    executed_step: Optional[PlanStep] = steps[0] if steps else None
    if executed_step:
        name = executed_step.get("tool") or ""
        args = executed_step.get("args") or {}
        try:
            resolved_args = _resolve_vars(args, vars_map)
            # extract_lab_report: paths 정규화 및 자동 주입
            if name == "extract_lab_report":
                try:
                    def _norm_paths(val: Any) -> List[str]:
                        out: List[str] = []
                        if val is None:
                            return out
                        # 이미 리스트/튜플인 경우
                        if isinstance(val, (list, tuple)):
                            # 단일 원소가 문자열화된 리스트인 경우 풀기 시도
                            if len(val) == 1 and isinstance(val[0], str):
                                s = val[0].strip()
                                if s.startswith("[") or s.startswith("("):
                                    try:
                                        import ast as _ast
                                        parsed = _ast.literal_eval(s)
                                        if isinstance(parsed, (list, tuple)):
                                            return [str(x) for x in parsed if str(x).strip()]
                                    except Exception:
                                        pass
                            return [str(x) for x in val if str(x).strip()]
                        # 문자열인 경우: 리스트 문자열이면 파싱, 아니면 단일 경로로 처리
                        if isinstance(val, str):
                            s = val.strip()
                            if s.startswith("[") or s.startswith("("):
                                try:
                                    import json as __json
                                    try:
                                        parsed = __json.loads(s)
                                    except Exception:
                                        import ast as _ast
                                        parsed = _ast.literal_eval(s)
                                    if isinstance(parsed, (list, tuple)):
                                        return [str(x) for x in parsed if str(x).strip()]
                                except Exception:
                                    pass
                            if s:
                                return [s]
                        # 기타 타입은 무시
                        return out

                    # 1) 현재 args.paths 정규화
                    if isinstance(resolved_args, dict) and "paths" in resolved_args:
                        normalized = _norm_paths(resolved_args.get("paths"))
                    else:
                        normalized = []
                    # 2) 비어있으면 vars.image_paths 사용
                    if not normalized and isinstance(vars_map, dict):
                        _ips = vars_map.get("image_paths")
                        normalized = _norm_paths(_ips)
                    # 3) 최종 반영
                    if normalized:
                        resolved_args = dict(resolved_args or {})
                        resolved_args["paths"] = normalized
                except Exception:
                    pass
            # 실행 전 로깅 (resolved args 포함)
            try:
                _ORCH_LOGGER.info(
                    "[EXECUTE] tool=%s | resolved_args=%s",
                    name,
                    _preview_data(resolved_args),
                )
            except Exception:
                pass

            # Local tool 우선 확인
            local_matched = None
            for lt in _build_local_tools(client):
                if lt.name == name:
                    local_matched = lt
                    break
            if local_matched is not None:
                observation = await local_matched.ainvoke(resolved_args)
            else:
                observation = await invoker.call(name, resolved_args)
            ok = True
            # 결과 저장
            save_as = executed_step.get("save_as")
            if save_as:
                vars_map[save_as] = observation
            else:
                # 자동 폴백 저장: 후속 단계에서 참조 가능하도록 마지막 관찰 값을 보관
                try:
                    vars_map["_last_observation"] = observation
                except Exception:
                    pass
            outs = dict(state.get("outputs") or {})
            outs[name] = observation
            state["outputs"] = outs

            # 병합된 검사결과(JSON)의 data.merged를 장기 메모리에 저장 (검색용)
            try:
                if name == "extract_lab_report" and observation is not None:
                    # observation은 문자열(JSON) 또는 dict일 수 있음
                    if isinstance(observation, str):
                        try:
                            env = _json.loads(observation)
                        except Exception:
                            env = None
                    elif isinstance(observation, dict):
                        env = observation
                    else:
                        env = None
                    if isinstance(env, dict) and env.get("stage") == "merge":
                        data = env.get("data") or {}
                        merged = (data or {}).get("merged")
                        if isinstance(merged, list) and merged:
                            # 병합 리스트 원형을 그대로 보존하여 단일 메모리로 저장합니다.
                            try:
                                from services.memory.memory_retriever import write_memories  # 지연 임포트
                            except Exception:
                                write_memories = None  # type: ignore
                            owner_id = (vars_map.get("owner_id") or "") if isinstance(vars_map, dict) else ""
                            cat_id = (vars_map.get("cat_id") or "") if isinstance(vars_map, dict) else ""
                            user_id = (vars_map.get("user_id") or os.environ.get("USER") or "default") if isinstance(vars_map, dict) else (os.environ.get("USER") or "default")

                            # 집계 정보(행 수, 날짜/병원 요약)를 계산합니다.
                            total_rows = 0
                            date_set: set[str] = set()
                            hosp_set: set[str] = set()
                            if all(isinstance(d, dict) and "tests" in d for d in merged):
                                for doc in merged:
                                    try:
                                        total_rows += len(doc.get("tests") or [])
                                    except Exception:
                                        pass
                                    dt = doc.get("inspection_date")
                                    if isinstance(dt, str) and dt:
                                        date_set.add(dt)
                                    hn = doc.get("hospital_name")
                                    if isinstance(hn, str) and hn:
                                        hosp_set.add(hn)
                            else:
                                total_rows = len(merged)
                                for r in merged:
                                    if not isinstance(r, dict):
                                        continue
                                    dt = r.get("inspection_date")
                                    if isinstance(dt, str) and dt:
                                        date_set.add(dt)
                                    hn = r.get("hospital_name")
                                    if isinstance(hn, str) and hn:
                                        hosp_set.add(hn)

                            dates = sorted(date_set)
                            hosps = sorted(hosp_set)
                            dates_txt = ",".join(dates) if dates else ""
                            hosps_txt = ",".join(hosps) if hosps else ""
                            content = f"[LabReport] rows={total_rows} dates={dates_txt} hospitals={hosps_txt}".strip()

                            md: Dict[str, Any] = {
                                "content": content,
                                "type": "lab_report",
                                "importance": 0.7,
                                "owner_id": owner_id,
                                "cat_id": cat_id,
                                "source": "lab_report",
                                "row_count": total_rows,
                                "inspection_dates": dates,
                                "hospital_names": hosps,
                                "lab_report_json": _json.dumps(merged, ensure_ascii=False),
                                "format": "LabReport.data",
                            }
                            # 저장 시도 (중복/예외 여부와 상관없이 UI 초기화를 위해 성공 플래그는 설정)
                            ids: List[str] = []
                            if write_memories:
                                try:
                                    ids = write_memories(user_id=user_id, memories=[md])
                                except Exception:
                                    # 저장 실패는 극히 예외적인 케이스로 간주
                                    pass
                            try:
                                vars_map["_lab_report_saved"] = True
                                vars_map["_lab_report_saved_summary"] = {
                                    "type": "lab_report",
                                    "dates": dates,
                                    "row_count": total_rows,
                                    "hospital_names": hosps,
                                    "ids": ids,
                                }
                            except Exception:
                                pass
            except Exception:
                # 메모리 저장 실패는 흐름에 영향 주지 않음
                pass
        except Exception as e:
            errs = list(state.get("errors") or [])
            errs.append(f"react_execute_node ({name}): {e}")
            state["errors"] = errs

        # tools_used 기록
        used = list(state.get("tools_used") or [])
        used.append({"name": name, "args": args, "ok": ok})
        state["tools_used"] = used

    # observation 로깅 (요약)
    try:
        if executed_step is not None:
            _obs_preview = _preview_data(observation, 1000)
            _ORCH_LOGGER.info(
                "[OBSERVE] tool=%s | ok=%s | observation=%s",
                (executed_step.get("tool") or ""),
                ok,
                _obs_preview,
            )
    except Exception:
        pass

    # history 누적
    hist = list(state.get("react_history") or [])
    hist.append({"step": executed_step, "observation": observation, "ok": ok})
    state["react_history"] = hist
    state["vars"] = vars_map
    return state

async def react_self_eval_node(state: OrchestratorState, model) -> OrchestratorState:
    """현재 관찰과 요청 대비 충분성을 자가 평가하고, 계속/종료 결정을 내립니다."""
    import json as _json
    user_req = (state.get("user_request") or "").strip()
    history = state.get("react_history") or []
    finish_hint = state.get("react_finish")
    iter_no = int(state.get("react_iteration") or 0)
    max_iters = int(state.get("react_max_iters") or 4)

    # 반복 한계 시 종료
    if iter_no + 1 >= max_iters:
        state["react_should_continue"] = False
        return state

    # 이미 plan 단계에서 finish를 제안한 경우 우선 종료
    if finish_hint:
        state["react_should_continue"] = False
        try:
            _ORCH_LOGGER.info("[SELF-EVAL] finish-hint present → stopping")
        except Exception:
            pass
        return state

    sys_prompt = (
        "당신은 품질 심사(Self-eval)자입니다. 최근 관찰까지 고려했을 때, 요청을 만족했는지 판단하세요.\n"
        "JSON만 출력하세요. 형식: {\"continue\": true|false}"
    )
    # history를 요약 문자열로 넘기지 않고 길이만 알려 간단화. 필요하면 직렬화하여 넘길 수 있음.
    user_prompt = (
        f"요청: {user_req}\n"
        f"수행된 단계 수: {len(history)}\n"
        "충분하면 {\"continue\": false}, 추가 조치가 필요하면 {\"continue\": true}만 출력."
    )
    try:
        msg = [{"role": "system", "content": sys_prompt}, {"role": "user", "content": user_prompt}]
        res = await model.ainvoke(msg)
        content = getattr(res, "content", None) or str(res)
        data = _json.loads(content)
        cont = bool(data.get("continue", False))
        state["react_should_continue"] = cont
        try:
            _ORCH_LOGGER.info("[SELF-EVAL] continue=%s | iter=%s/%s | history_len=%s", cont, iter_no, max_iters, len(history))
        except Exception:
            pass
    except Exception as e:
        errs = list(state.get("errors") or [])
        errs.append(f"react_self_eval_node: {e}")
        state["errors"] = errs
        state["react_should_continue"] = False
    return state

def react_compose_node(state: OrchestratorState) -> OrchestratorState:
    """ReAct 루프 종료 시 사용자 메시지 생성."""
    finish = state.get("react_finish") or {}

    # MergeEnvelope(JSON) 요약을 앞부분에 덧붙이는 보조 함수
    def _render_merge_summary(prefix_src: Any) -> Optional[str]:
        try:
            import json as _json
            if not prefix_src:
                return None
            # 문자열이면 JSON 파싱 시도
            if isinstance(prefix_src, str):
                try:
                    env = _json.loads(prefix_src)
                except Exception:
                    return None
            elif isinstance(prefix_src, dict):
                env = prefix_src
            else:
                return None

            if not isinstance(env, dict):
                return None
            stage = env.get("stage")
            data = env.get("data") or {}
            meta = env.get("meta") or {}
            if stage != "merge":
                # 병합 결과가 아니면 스킵
                return None

            lines: List[str] = []
            # 메타데이터 섹션
            if isinstance(meta, dict) and meta:
                lines.append("메타데이터")
                lines.append("")
                for k, v in meta.items():
                    try:
                        lines.append(f"- {k}: {v}")
                    except Exception:
                        lines.append(f"- {k}: <unprintable>")
                lines.append("")

            # 검사항목 테이블 섹션
            merged = (data or {}).get("merged")
            if isinstance(merged, list) and merged:
                # 선호 컬럼 순서
                preferred = [
                    "name", "test", "analyte",
                    "value", "result", "unit",
                    "flag", "abnormal",
                    "reference", "reference_range", "ref_range", "low", "high",
                ]
                # 실제 항목들의 키 수집
                keys = []
                try:
                    for item in merged[:12]:
                        if isinstance(item, dict):
                            for k in item.keys():
                                if k not in keys:
                                    keys.append(k)
                except Exception:
                    pass
                # 표시할 컬럼 결정
                show_cols = [c for c in preferred if c in keys]
                # 최소 안전장치
                if not show_cols and keys:
                    show_cols = keys[:6]

                if show_cols:
                    # 마크다운 표 렌더링
                    header = " | ".join(show_cols)
                    sep = " | ".join(["---"] * len(show_cols))
                    lines.append("검사항목")
                    lines.append("")
                    lines.append(header)
                    lines.append(sep)
                    for item in merged[:50]:  # 과도한 행 방지
                        if not isinstance(item, dict):
                            continue
                        row = []
                        for c in show_cols:
                            val = item.get(c, "")
                            try:
                                s = str(val)
                            except Exception:
                                s = "<unprintable>"
                            # 파이프/개행 최소 이스케이프
                            s = s.replace("|", "\\|").replace("\n", " ")
                            row.append(s)
                        lines.append(" | ".join(row))
                    lines.append("")

            return "\n".join(lines) if lines else None
        except Exception:
            return None
    if isinstance(finish, dict):
        use = finish.get("use")
        value = finish.get("value")
        if use == "var":
            varname = str(value) if value is not None else ""
            if varname and varname in (state.get("vars") or {}):
                base_msg = f"결과: {(state.get('vars') or {}).get(varname)}"
                # 병합 결과 요약이 가능하면 앞에 붙임
                merge_src = (state.get("vars") or {}).get(varname)
                prefix = _render_merge_summary(merge_src)
                state["message"] = (prefix + "\n\n" + base_msg) if prefix else base_msg
                try:
                    _ORCH_LOGGER.info("[COMPOSE] finish use=var | var=%s", varname)
                except Exception:
                    pass
                return state
        if use == "message" and isinstance(value, str):
            # 가능하면 마지막 출력 중 병합 결과를 찾아 앞에 붙임
            outs = state.get("outputs") or {}
            merge_src = None
            # 우선 extract_lab_report 결과를 시도
            if "extract_lab_report" in outs:
                merge_src = outs.get("extract_lab_report")
            elif outs:
                # 최근 키의 값을 시도
                merge_src = outs.get(list(outs.keys())[-1])
            prefix = _render_merge_summary(merge_src)
            state["message"] = (prefix + "\n\n" + value) if prefix else value
            try:
                _ORCH_LOGGER.info("[COMPOSE] finish use=message")
            except Exception:
                pass
            return state

    # 폴백: 마지막 관찰 또는 기존 compose_auto 로직과 유사하게 처리
    hist = state.get("react_history") or []
    if hist and isinstance(hist[-1], dict):
        obs = hist[-1].get("observation")
        if obs is not None:
            base_msg = f"최종 관찰: {obs}"
            prefix = _render_merge_summary(obs)
            state["message"] = (prefix + "\n\n" + base_msg) if prefix else base_msg
            try:
                _ORCH_LOGGER.info("[COMPOSE] fallback last observation")
            except Exception:
                pass
            return state

    # 추가 폴백: 마지막 출력 또는 오류/빈 결과 안내
    outs = state.get("outputs") or {}
    if outs:
        last_key = list(outs.keys())[-1]
        base_msg = f"{last_key} 결과: {outs.get(last_key)}"
        prefix = _render_merge_summary(outs.get(last_key))
        state["message"] = (prefix + "\n\n" + base_msg) if prefix else base_msg
        try:
            _ORCH_LOGGER.info("[COMPOSE] fallback outputs last_key=%s", last_key)
        except Exception:
            pass
        return state
    if state.get("errors"):
        state["message"] = "요청을 처리하는 중 일부 단계에서 오류가 발생했습니다."
    else:
        state["message"] = "결과가 없습니다."
    try:
        _ORCH_LOGGER.info("[COMPOSE] fallback empty or errors present")
    except Exception:
        pass
    return state

def build_react_rag_graph(model, client) -> Any:
    graph = StateGraph(OrchestratorState)

    async def _plan(state: OrchestratorState) -> OrchestratorState:
        return await react_plan_node(state, model, client)

    async def _exec(state: OrchestratorState) -> OrchestratorState:
        return await react_execute_node(state, client)

    async def _self_eval(state: OrchestratorState) -> OrchestratorState:
        return await react_self_eval_node(state, model)

    graph.add_node("plan", _plan)
    graph.add_node("execute", _exec)
    graph.add_node("self_eval", _self_eval)
    graph.add_node("compose_react", react_compose_node)

    graph.set_entry_point("plan")
    graph.add_edge("plan", "execute")
    graph.add_edge("execute", "self_eval")

    def _continue_or_finish(state: OrchestratorState) -> str:
        # 반복 카운터 증가
        it = int(state.get("react_iteration") or 0)
        state["react_iteration"] = it + 1
        # self_eval 결과로 분기
        if state.get("react_should_continue"):
            return "plan"
        return "compose_react"

    graph.add_conditional_edges("self_eval", _continue_or_finish, {"plan": "plan", "compose_react": "compose_react"})

    return graph.compile()

async def run_react_rag(client, model, user_request: str, allowed_tools: Optional[List[str]] = None, max_iters: int = 4, extra_vars: Optional[Dict[str, Any]] = None) -> OrchestratorState:
    """ReAct RAG 루프 실행 엔트리포인트.

    - user_request: 자연어 요청
    - allowed_tools: 사용 허용 도구(예: ["search_kb", "rerank", "read_doc"]) 
    - max_iters: 최대 반복 횟수(안전 장치)
    """
    app = build_react_rag_graph(model, client)
    init: OrchestratorState = {
        "user_request": user_request,
        "allowed_tools": allowed_tools or [],
    "vars": dict(extra_vars or {}),
        "outputs": {},
        "errors": [],
        "warnings": [],
        "tools_used": [],
        "react_iteration": 0,
        "react_max_iters": int(max_iters),
        "react_history": [],
    }
    result: OrchestratorState = await app.ainvoke(init)

    # 스몰토크 친화 폴백: 합성 결과가 비어 있으면 직접 답변을 생성합니다.
    try:
        msg = result.get("message")
        outs = result.get("outputs") or {}
        errs = result.get("errors") or []
        no_effective_plan = (not msg or str(msg).strip() == "실행할 계획이 없었습니다.") and (not outs) and (not errs)
        if no_effective_plan:
            sys_prompt = (
                "당신은 친절하고 간결한 한국어 비서입니다. 작은 인사말이나 잡담에도 따뜻하게 응답하세요.\n"
                "불필요한 도구 사용 계획은 만들지 말고, 지금 입력에 친근하게 답변만 출력하세요."
            )
            vars_map = dict(extra_vars or {})
            try:
                pinned = vars_map.get("pinned_core_facts")
                if pinned:
                    sys_prompt += f"\n[핵심 사실 요약]\n{str(pinned)[:800]}\n"
            except Exception:
                pass

            user_prompt = user_request.strip()
            ai_res = await model.ainvoke([
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt},
            ])
            content = getattr(ai_res, "content", None) or str(ai_res)
            result["message"] = content
    except Exception:
        pass

    return result
