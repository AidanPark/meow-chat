"""
Meow Chat 오케스트레이터 (LangGraph 기반)
=======================================================================

이 모듈은 MultiServerMCPClient로 노출된 여러 MCP 서버 도구(Math/Weather …)를
"상태(State)를 가진 그래프"로 오케스트레이션하기 위한 구현입니다. 크게 두 가지 모드가 포함됩니다.

1) 규칙 기반 스켈레톤(Math/Weather)
    - router → (math | weather) → compose 의 단순 파이프라인
    - 목적: "작업 라우팅 → 도구 호출 → 결과 합성"의 최소 패턴을 익히기 위한 예시
    - task="math" 일 때: add/multiply/… 같은 MathUtilityServer 도구를 호출
    - task="weather" 일 때: get_weather/get_forecast/… 같은 WeatherAPIServer 도구를 호출

2) LLM 플래너 기반 자동 계획(Always-On Planner)
    - planner(LLM) → executor(결정적 실행) → compose 의 구조
    - 모델이 JSON 계획(PlanSpec)을 생성하고, 실행기는 그 계획을 "결정적으로" 수행합니다.
    - 장점: 시나리오마다 코드를 새로 짜지 않고, 허용된 도구 범위 내에서 다양한 요구를 일반화
    - 안전장치: 허용 도구 화이트리스트, 단계 수 제한, 오류 누적 및 관찰(툴 사용 기록)

핵심 개념
-----------
- OrchestratorState: 그래프를 흐르는 단일 상태(입력/출력/오류/도구사용/플랜/변수 등)
- MCPToolInvoker: MCP 도구를 이름으로 안전하게 찾아 비동기로 호출하는 래퍼
- 노드(Node): 순수 함수(또는 async 함수)로 상태를 입력받아 갱신 후 반환
- 엣지(Edge): 다음 노드로의 연결. 조건부 엣지로 분기 가능

상태(State) 설계 요약
----------------------
- task: "math" | "weather" (규칙 스켈레톤용)
- inputs/outputs: 각 노드가 읽고/쓰는 I/O 컨테이너
- errors/warnings: 단계별 예외/경고 누적(Compose에서 사용자 메시지로 환원 가능)
- tools_used: {name, args, ok} 리스트로 관찰성 확보(UI tool_history에 반영)
- user_request/plan/vars/primary_output: LLM 플래너 모드에서 사용

LLM 플래너 모드 작동 방식
---------------------------
1) planner_node: 현재 허용된 MCP 도구 목록과 사용자 요청을 바탕으로 JSON 계획(steps)을 생성
    - 형식: PlanSpec {version, steps: [PlanStep], primary, limits}
    - 각 Step: {tool, args, save_as, expect?}
    - 안전장치: 허용 도구(화이트리스트) 필터, 단계 수 상한(max_steps)
2) executor_node: 계획을 "결정적으로" 수행
    - ${var} 템플릿을 vars 맵으로 치환
    - MCPToolInvoker로 도구를 호출(비동기)
    - 결과를 vars[save_as], outputs[tool]에 저장, tools_used에 기록
    - 실패는 errors에 누적하고 계속 진행(가능한 정보로 최대한 응답)
3) compose_auto_node: primary_output 또는 마지막 결과를 간단히 합성(필요 시 모델 요약으로 대체 가능)

운영/확장 포인트
------------------
- 재시도/타임아웃/회로 차단: MCPToolInvoker에 추가해 안정성 강화
- 병렬 실행/Map 노드: 여러 입력(batch)에 대한 동시 처리(동시성 제한 필수)
- 계획 검증 고도화: expect/type/range 검증, 금지 도구/인자 필터, 비용 상한
- 관찰성: step별 ms, 호출 횟수, 성공률, 오류 사유 등을 로깅/메트릭으로 적재

주의 사항
----------
- Weather 도구처럼 문자열을 반환하는 경우, 후속 수치 연산이 필요하면 플래너 프롬프트로 파싱을 유도하거나
  MCP 서버에서 구조화(JSON) 형태로 반환하도록 개선하는 것이 견고합니다.
- 본 파일은 "오케스트레이션" 레이어이며, UI 연결/토글은 frontend/app.py 에서 처리합니다.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, TypedDict, Union

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

    # LLM 플래너용 필드
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


# (Planner 관련 코드는 제거되었습니다)

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
        for t in tools:
            name = getattr(t, "name", None)
            if not name:
                continue
            if allowed and name not in allowed:
                continue
            desc = getattr(t, "description", None)
            # 설명은 너무 길 경우 앞부분만 사용
            if isinstance(desc, str) and len(desc) > 260:
                desc = desc[:260] + "…"
            available.append({"name": name, "desc": desc or ""})
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
        "args에서는 제공된 변수들을 ${변수명} 형태로 참조할 수 있습니다(예: ${owner_id}, ${cat_id}).\n"
    )
    # 도구 선택 규칙 힌트(절차 강제가 아닌 선택 원칙)
    sys_prompt += (
        "\n[도구 선택 규칙]\n"
        "- 이미지 첨부가 있고 검사/혈액/수치/결과지 분석이 필요하면, 우선 이미지에서 텍스트를 확보하세요(예: ocr_image_file).\n"
        "- 검사 결과를 구조화/해석하려면, OCR 결과(OCRResultEnvelope JSON)를 구조화 도구에 입력하세요(예: extract_lab_report).\n"
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
            observation = await invoker.call(name, resolved_args)
            ok = True
            # 결과 저장
            save_as = executed_step.get("save_as")
            if save_as:
                vars_map[save_as] = observation
            outs = dict(state.get("outputs") or {})
            outs[name] = observation
            state["outputs"] = outs
        except Exception as e:
            errs = list(state.get("errors") or [])
            errs.append(f"react_execute_node ({name}): {e}")
            state["errors"] = errs

        # tools_used 기록
        used = list(state.get("tools_used") or [])
        used.append({"name": name, "args": args, "ok": ok})
        state["tools_used"] = used

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
    except Exception as e:
        errs = list(state.get("errors") or [])
        errs.append(f"react_self_eval_node: {e}")
        state["errors"] = errs
        state["react_should_continue"] = False
    return state


def react_compose_node(state: OrchestratorState) -> OrchestratorState:
    """ReAct 루프 종료 시 사용자 메시지 생성."""
    finish = state.get("react_finish") or {}
    if isinstance(finish, dict):
        use = finish.get("use")
        value = finish.get("value")
        if use == "var":
            varname = str(value) if value is not None else ""
            if varname and varname in (state.get("vars") or {}):
                state["message"] = f"결과: {(state.get('vars') or {}).get(varname)}"
                return state
        if use == "message" and isinstance(value, str):
            state["message"] = value
            return state

    # fallback: 마지막 관찰 또는 기존 compose_auto 로직과 유사하게 처리
    hist = state.get("react_history") or []
    if hist and isinstance(hist[-1], dict):
        obs = hist[-1].get("observation")
        if obs is not None:
            state["message"] = f"최종 관찰: {obs}"
            return state

    # 추가 fallback: 마지막 출력 또는 오류/빈 결과 안내
    outs = state.get("outputs") or {}
    if outs:
        last_key = list(outs.keys())[-1]
        state["message"] = f"{last_key} 결과: {outs.get(last_key)}"
        return state
    if state.get("errors"):
        state["message"] = "요청을 처리하는 중 일부 단계에서 오류가 발생했습니다."
    else:
        state["message"] = "결과가 없습니다."
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

    # Friendly fallback for small-talk: if compose ends up with no content, answer directly
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
