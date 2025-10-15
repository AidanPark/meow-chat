# ============================================================
# TEST_INFO_MAP : 공통 검사 항목 정의 (code → name, meaning, description)
# ============================================================

TEST_INFO_MAP = {
    # ---------- 화학 분석 ----------
    "ALB": {
        "name": "Albumin",
        "meaning": "혈중 주요 단백질 (간 합성)",
        "description": "간에서 합성되는 주요 단백질로 삼투압 유지와 운반 역할. "
                       "저알부민혈증은 간부전, 단백소실, 염증, 탈수 등을 시사."
    },
    "ALKP": {
        "name": "Alkaline Phosphatase",
        "meaning": "알칼리성 인산분해효소",
        "description": "간, 담도, 뼈에서 생성되는 효소로 담즙정체, 골질환, 쿠싱증후군 시 상승."
    },
    "ALP": {
        "name": "Alkaline Phosphatase",
        "meaning": "알칼리성 인산분해효소",
        "description": "간, 담도, 뼈에서 생성되는 효소로 담즙정체, 골질환, 쿠싱증후군 시 상승."
    },
    "ALT": {
        "name": "Alanine Aminotransferase",
        "meaning": "간세포 손상 지표 효소",
        "description": "간세포 내 효소로 손상 시 혈중 상승. 급성 간염, 약물성 손상 시 민감."
    },
    "AST": {
        "name": "Aspartate Aminotransferase",
        "meaning": "간 및 근육 손상 지표 효소",
        "description": "간, 심근, 근육세포 내 효소. ALT와 함께 상승 시 간손상, 단독 상승 시 근손상 가능."
    },
    "BUN": {
        "name": "Blood Urea Nitrogen",
        "meaning": "혈중 요소질소 (신장 기능 지표)",
        "description": "단백질 대사 산물로, 신장 배설 기능 반영. 탈수·신부전·GI 출혈 시 상승."
    },
    "CRE": {
        "name": "Creatinine",
        "meaning": "사구체 여과율(GFR) 지표",
        "description": "근육 대사산물로 신장 여과기능 반영. 신부전 시 상승, 근육량에 따라 변동."
    },
    "CREA": {
        "name": "Creatinine",
        "meaning": "사구체 여과율(GFR) 지표",
        "description": "근육 대사산물로 신장 여과기능 반영. 신부전 시 상승, 근육량에 따라 변동."
    },
    "TP": {
        "name": "Total Protein",
        "meaning": "총 단백질 (ALB+GLOB)",
        "description": "혈장 내 단백질 총량. 탈수 시 상승, 단백소실·간질환 시 감소."
    },
    "GLOB": {
        "name": "Globulin (calculated)",
        "meaning": "면역 단백질 (글로불린)",
        "description": "면역글로불린·급성기 단백 포함. 염증·감염 시 상승, 단백소실·간질환 시 감소."
    },
    "GLU": {
        "name": "Glucose",
        "meaning": "혈당",
        "description": "에너지 대사 주요 지표. 당뇨병, 스트레스 시 상승, 패혈증·간부전 시 감소."
    },
    "CHOL": {
        "name": "Cholesterol",
        "meaning": "총 콜레스테롤",
        "description": "지질대사 반영. 갑상선 저하, 쿠싱증후군, 담즙정체 시 상승."
    },
    "TCHO": {
        "name": "Total Cholesterol",
        "meaning": "총 콜레스테롤",
        "description": "지질대사 반영. 갑상선 저하, 쿠싱증후군, 담즙정체 시 상승."
    },
    "TG": {
        "name": "Triglyceride",
        "meaning": "중성지방",
        "description": "지질대사 지표. 식후 상승, 당뇨·쿠싱증후군에서 증가 가능."
    },
    "Ca": {
        "name": "Calcium",
        "meaning": "혈중 칼슘 농도",
        "description": "뼈·신경·근육 기능에 필수. 고칼슘혈증은 종양, 저칼슘혈증은 경련 유발."
    },
    "PHOS": {
        "name": "Phosphorus",
        "meaning": "무기 인산염",
        "description": "뼈 대사 및 신장 기능 반영. 신부전 시 상승, 부갑상선 항진 시 감소."
    },
    "IP": {
        "name": "Inorganic Phosphorus",
        "meaning": "무기 인산염",
        "description": "뼈 대사 및 신장 기능 반영. 신부전 시 상승, 부갑상선 항진 시 감소."
    },
    "GGT": {
        "name": "Gamma-Glutamyl Transferase",
        "meaning": "감마-GT (간·담즙 효소)",
        "description": "담즙정체, 간세포 손상에서 증가. 고양이에선 민감도 낮음."
    },
    "LDH": {
        "name": "Lactate Dehydrogenase",
        "meaning": "젖산탈수소효소",
        "description": "간·근육·심근 손상 시 상승. 비특이적 조직 손상 지표."
    },
    "CPK": {
        "name": "Creatine Phosphokinase",
        "meaning": "근육 손상 효소",
        "description": "골격근·심근 손상 시 상승. 발작, 근육 외상에서도 증가."
    },
    "v-AMYL": {
        "name": "Amylase (Vet)",
        "meaning": "수의전용 아밀라아제",
        "description": "췌장 및 장기에서 분비. 췌장염 시 상승, 신부전 시도 상승 가능."
    },
    "v-LIP": {
        "name": "Lipase (Vet)",
        "meaning": "수의전용 리파아제",
        "description": "지방분해효소. 췌장염 등에서 상승, v-AMYL보다 특이도 높음."
    },
    "TBIL": {
        "name": "Total Bilirubin",
        "meaning": "총 빌리루빈 (담즙 색소)",
        "description": "적혈구 파괴 및 간 배설 반영. 간질환, 용혈, 담즙정체 시 상승."
    },
    "NH3": {
        "name": "Ammonia",
        "meaning": "암모니아 (간 기능 지표)",
        "description": "단백질 대사 부산물. 간기능 저하, 문맥전신단락에서 상승."
    },
    "TCO2": {
        "name": "Total CO₂ (Bicarbonate)",
        "meaning": "총 이산화탄소 (중탄산 포함)",
        "description": "대사성 산염기 균형 반영. 산증 시 감소, 알칼리증 시 증가."
    },
    "tCO2": {
        "name": "Total CO₂ (Bicarbonate)",
        "meaning": "총 이산화탄소 (중탄산 포함)",
        "description": "대사성 산염기 균형 반영. 산증 시 감소, 알칼리증 시 증가."
    },
    "Na": {
        "name": "Sodium",
        "meaning": "혈중 나트륨 농도",
        "description": "체액 삼투압 조절. 탈수 시 상승, 부신기능저하(Addison's) 시 감소."
    },
    "Na+": {
        "name": "Sodium",
        "meaning": "혈중 나트륨 농도",
        "description": "체액 삼투압 조절. 탈수 시 상승, 부신기능저하(Addison's) 시 감소."
    },
    "K": {
        "name": "Potassium",
        "meaning": "혈중 칼륨 농도",
        "description": "세포내 주요 양이온. 저칼륨혈증은 근력저하, 고칼륨혈증은 부정맥·심정지 유발."
    },
    "K+": {
        "name": "Potassium",
        "meaning": "혈중 칼륨 농도",
        "description": "세포내 주요 양이온. 저칼륨혈증은 근력저하, 고칼륨혈증은 부정맥·심정지 유발."
    },
    "Cl": {
        "name": "Chloride",
        "meaning": "혈중 염소이온 농도",
        "description": "전해질 균형 반영. 구토 시 감소, 산증 보상 시 증가."
    },
    "Cl-": {
        "name": "Chloride",
        "meaning": "혈중 염소이온 농도",
        "description": "전해질 균형 반영. 구토 시 감소, 산증 보상 시 증가."
    },
    "Mg": {
        "name": "Magnesium",
        "meaning": "마그네슘 농도",
        "description": "효소 활성 및 신경근 기능 조절. 저마그네슘혈증은 경련·부정맥 유발 가능."
    },
    "T4": {
        "name": "Total Thyroxine",
        "meaning": "총 갑상선호르몬(T4)",
        "description": "갑상선 기능 평가 지표. 고양이 항진증, 개 저하증 진단에 핵심."
    },
    "BA": {
        "name": "Bile Acids",
        "meaning": "담즙산 (간 기능 지표)",
        "description": "간의 담즙 배설·재흡수 반영. 문맥전신단락, 간부전 평가에 사용."
    },
    "T.Protein": {
        "name": "Total Protein",
        "meaning": "총 단백질 (Total Protein)",
        "description": "혈장 내 단백질 농도. 알부민과 글로불린의 합. 탈수 시 증가, 간질환·단백질 손실 시 감소."
    },
    "Albumin": {
        "name": "Albumin",
        "meaning": "알부민 (Albumin)",
        "description": "혈장 내 주요 단백질. 간 합성 기능 및 삼투압 유지에 중요. 간부전, 신증후군 시 감소."
    },
    "Globulin": {
        "name": "Globulin",
        "meaning": "글로불린 (Globulin)",
        "description": "면역글로불린 및 급성기 단백질. 염증, 면역반응, 감염 시 증가."
    },
    "T.Billirubin": {
        "name": "Total Bilirubin",
        "meaning": "총 빌리루빈 (Total Bilirubin)",
        "description": "헤모글로빈 대사 산물. 간세포 손상, 담도 폐쇄 시 증가."
    },
    "Na/K": {
        "name": "Sodium/Potassium Ratio",
        "meaning": "나트륨/칼륨 비율",
        "description": "전해질 균형을 반영. Na/K < 27 은 Addison's disease(부신피질 기능저하) 의심 지표."
    },
    "BUN/CRE": {
        "name": "BUN/Creatinine Ratio",
        "meaning": "요소질소/크레아티닌 비율",
        "description": "신기능 평가 보조 지표. 탈수나 GI 출혈 시 상승, 간부전 시 감소."
    },

    # ---------- CBC ----------
    "WBC": {
        "name": "White Blood Cells",
        "meaning": "백혈구 수",
        "description": "면역반응, 염증 지표. 상승 시 감염·염증, 감소 시 골수억제."
    },
    "RBC": {
        "name": "Red Blood Cells",
        "meaning": "적혈구 수",
        "description": "산소 운반 세포. 빈혈, 출혈, 탈수 평가."
    },
    "HGB": {
        "name": "Hemoglobin",
        "meaning": "헤모글로빈 농도",
        "description": "산소 운반 단백질. 빈혈 평가에 사용."
    },
    "HCT": {
        "name": "Hematocrit",
        "meaning": "적혈구 용적률",
        "description": "혈액 중 적혈구 비율. 탈수 시 상승, 빈혈 시 감소."
    },
    "MCV": {
        "name": "Mean Corpuscular Volume",
        "meaning": "평균 적혈구 용적",
        "description": "적혈구 크기. 거대적혈구(재생성 빈혈), 소적혈구(철결핍) 감별."
    },
    "MCHC": {
        "name": "Mean Corpuscular Hgb Concentration",
        "meaning": "평균 혈색소 농도",
        "description": "적혈구 내 Hb 농도. 저색소성 빈혈, 탈수 감별에 도움."
    },
    "PLT": {
        "name": "Platelets",
        "meaning": "혈소판 수",
        "description": "혈액응고에 관여. 감소 시 출혈 위험, 증가 시 염증 반응 가능."
    },
    "RDW": {
        "name": "Red Cell Distribution Width",
        "meaning": "적혈구 분포 폭",
        "description": "적혈구 크기 변동성. 재생성 빈혈·영양결핍 감별에 도움."
    },
    "RETIC%": {
        "name": "Reticulocyte %",
        "meaning": "망상적혈구 비율",
        "description": "골수의 적혈구 생성능 반영. 재생성 빈혈 여부 평가."
    },
    "RETIC#": {
        "name": "Reticulocyte #",
        "meaning": "망상적혈구 절대수",
        "description": "골수 재생능의 정량 평가 지표."
    },
    "RETIC": {
        "name": "Reticulocyte Count",
        "meaning": "망상적혈구 수 (절대수)",
        "description": "골수의 적혈구 생성능 반영. 재생성 빈혈에서 증가하며, 무재생성 빈혈이나 골수기능 저하 시 감소."
    },
    "RETHGB": {
        "name": "Reticulocyte Hemoglobin Content",
        "meaning": "망상적혈구 헤모글로빈 함량",
        "description": "신생 적혈구(망상적혈구)에 포함된 평균 헤모글로빈 양을 반영. 철 결핍성 빈혈 조기 평가에 사용됨."
    },
    "LYMPHO(%)": {
        "name": "Lymphocytes %",
        "meaning": "림프구 백분율",
        "description": "백혈구 중 림프구의 비율. 바이러스 감염, 만성 염증, 면역반응 시 증가."
    },
    "Mono(%)": {
        "name": "Monocytes %",
        "meaning": "단핵구 백분율",
        "description": "백혈구 중 단핵구의 비율. 만성 염증, 조직 손상 회복기에 증가."
    },
    "EOS(%)": {
        "name": "Eosinophils %",
        "meaning": "호산구 백분율",
        "description": "알레르기 반응, 기생충 감염에서 증가. 스테로이드 투여 시 감소."
    },
    "BASO(%)": {
        "name": "Basophils %",
        "meaning": "호염구 백분율",
        "description": "희귀 항목. 알레르기, 만성 염증, 기생충 감염에서 약간 증가할 수 있음."
    },
    "NEUT": {
        "name": "Neutrophils (Absolute)",
        "meaning": "호중구 절대수",
        "description": "세균 감염, 급성 염증 시 증가. 면역저하나 바이러스 감염 시 감소."
    },
    "LYMPH": {
        "name": "Lymphocytes (Absolute)",
        "meaning": "림프구 절대수",
        "description": "면역 활성화, 바이러스 감염 시 증가. 스트레스, 코르티솔 상승 시 감소."
    },
    "MONO": {
        "name": "Monocytes (Absolute)",
        "meaning": "단핵구 절대수",
        "description": "만성 감염, 조직 손상 회복기에서 증가. 골수 기능 저하 시 감소."
    },
    "BASO": {
        "name": "Basophils (Absolute)",
        "meaning": "호염구 절대수",
        "description": "희귀 항목. 알레르기, 기생충 감염 등에서 약간 증가할 수 있음."
    },
    "NEUTROPHILS(%)": {
        "name": "Neutrophils %",
        "meaning": "호중구 백분율 (NEU%)",
        "description": "백혈구 중 호중구의 비율. 세균 감염·염증 시 상승, 바이러스 감염·면역억제 시 감소."
    },    
    "LYM%": {
        "name": "Lymphocytes %",
        "meaning": "림프구 비율",
        "description": "면역반응, 바이러스 감염 반영. 증가 시 만성염증, 감소 시 스트레스 반응."
    },
    "MONO%": {
        "name": "Monocytes %",
        "meaning": "단핵구 비율",
        "description": "조직 손상 후 회복기·만성염증 반영."
    },
    "GRAN%": {
        "name": "Granulocytes %",
        "meaning": "호중구(과립구) 비율",
        "description": "세균 감염, 급성 염증 시 상승."
    },
    "EOS%": {
        "name": "Eosinophils %",
        "meaning": "호산구 비율",
        "description": "기생충·알레르기 반응 반영."
    },
    "NEU%": {
        "name": "Neutrophils %",
        "meaning": "호중구 비율",
        "description": "세균 감염, 염증성 질환 시 상승."
    },
    "RDW-CV": {
        "name": "Red Cell Distribution Width (CV)",
        "meaning": "적혈구 분포 폭 (변이계수)",
        "description": "적혈구 크기의 불균일성 지표. 빈혈의 종류 감별에 사용."
    },
    "RETIC-HGB": {
        "name": "Reticulocyte Hemoglobin Content",
        "meaning": "망상적혈구 헤모글로빈 함량",
        "description": "신선한 적혈구의 철 결핍 여부 평가. 조기 철결핍 탐지에 유용."
    },
    "PCT": {
        "name": "Plateletcrit",
        "meaning": "혈소판 용적률",
        "description": "전체 혈액 부피 중 혈소판이 차지하는 비율. 혈소판 감소증 평가에 사용."
    },    
    "Lymph#": {
        "name": "Lymphocytes (Absolute)",
        "meaning": "림프구 절대수 (Lymphocyte #)",
        "description": "면역 활성화 또는 바이러스 감염 시 증가. 스트레스, 코르티솔 상승 시 감소."
    },
    "GRAN#": {
        "name": "Granulocytes (Absolute)",
        "meaning": "과립구 절대수 (호중구+호산구+호염구)",
        "description": "세균감염, 염증 반응 시 증가. 골수 억제나 면역저하 시 감소."
    },
    "Lymph%": {
        "name": "Lymphocytes %",
        "meaning": "림프구 백분율",
        "description": "백혈구 중 림프구 비율. 바이러스 감염, 만성 염증 시 증가."
    },
    "PCT%": {
        "name": "Plateletcrit %",
        "meaning": "혈소판 용적률 비율",
        "description": "전체 혈액 부피에서 혈소판이 차지하는 비율. 혈소판 감소증 평가에 사용."
    },
    "PDW": {
        "name": "Platelet Distribution Width",
        "meaning": "혈소판 크기 분포 폭",
        "description": "혈소판 크기의 다양성 지표. 혈소판 생성·파괴 이상 평가에 사용."
    },
    "RDW-SD": {
        "name": "Red Cell Distribution Width (SD)",
        "meaning": "적혈구 분포 폭 (표준편차)",
        "description": "적혈구 크기의 불균일성 정도를 나타냄. 빈혈 감별에 사용."
    },

    # ---------- 혈가스 ----------
    "pH": {"name": "Blood pH", "meaning": "혈액 산도", "description": "정상 7.35-7.45. 대사성·호흡성 산·염기 상태 평가."},
    "pCO2": {"name": "Partial Pressure of CO₂", "meaning": "이산화탄소 분압", "description": "호흡성 산·염기 평가 지표. 상승 시 호흡저하."},
    "pO2": {"name": "Partial Pressure of O₂", "meaning": "산소 분압", "description": "폐 환기 및 산소화 상태 반영."},
    "HCO3": {"name": "Bicarbonate", "meaning": "중탄산이온 농도", "description": "대사성 산·염기 균형 지표. 감소 시 산증."},
    "LAC": {"name": "Lactate", "meaning": "젖산 농도", "description": "저산소증, 쇼크, 대사장애 시 상승."},
    "PH(T)": {
        "name": "Temperature-corrected pH",
        "meaning": "체온 보정된 혈액 pH",
        "description": "환자의 체온을 반영한 pH. 체온 상승 시 감소, 저체온 시 증가."
    },
    "PCO2(T)": {
        "name": "Temperature-corrected pCO₂",
        "meaning": "체온 보정된 이산화탄소 분압",
        "description": "체온 변화에 따라 CO₂ 용해도를 보정한 값. 고체온 시 감소, 저체온 시 증가."
    },
    "HCO3-Std": {
        "name": "Standard Bicarbonate",
        "meaning": "표준 중탄산이온 농도",
        "description": "PaCO₂ 40mmHg 기준에서의 HCO₃⁻ 농도. 대사성 산·염기 불균형 평가에 사용."
    },
    "BB": {
        "name": "Buffer Base",
        "meaning": "완충염기량",
        "description": "혈액 내 모든 완충염기의 총량. 대사성 산증·알칼리증 평가 지표."
    },
    "BE-Ecf": {
        "name": "Base Excess (Extracellular Fluid)",
        "meaning": "세포외액 기준 염기과잉",
        "description": "세포외액 공간 기준 대사성 산·염기 불균형의 정도를 평가."
    },
    "PO2(T)": {
        "name": "Temperature-corrected pO₂",
        "meaning": "체온 보정된 산소 분압",
        "description": "체온에 따라 산소 용해도를 보정한 값. 고체온 시 감소, 저체온 시 증가."
    },
    "pO2(A-a)": {
        "name": "Alveolar-Arterial Oxygen Gradient",
        "meaning": "폐포–동맥 산소분압차 (A-aDO₂)",
        "description": "폐의 산소 확산 효율 평가. 30mmHg 이상은 폐 확산장애 또는 단락(shunt) 의심."
    },

    # ---------- 전해질 및 미네랄 ----------
    "iCa-pH7.4": {
        "name": "Ionized Calcium (pH 7.4)",
        "meaning": "pH 7.4 기준 이온화 칼슘 농도",
        "description": "혈액 pH 7.4로 보정한 생리적 활성 칼슘 농도. 대사성 산·염기 상태 평가에 사용."
    },    

    # ---------- 면역 및 염증 ----------
    "FSAA": {
        "name": "Feline Serum Amyloid A",
        "meaning": "고양이 혈청 아밀로이드 A",
        "description": "고양이 염증·감염의 민감한 급성기 단백질. feline-specific 염증지표."
    },

    # ---------- 응고 ----------
    "PT": {"name": "Prothrombin Time", "meaning": "프로트롬빈 시간", "description": "외인성 응고경로 평가. 비타민K 결핍, 간질환 시 연장."},
    "aPTT": {"name": "Activated Partial Thromboplastin Time", "meaning": "활성화 부분 트롬보플라스틴 시간", "description": "내인성 응고경로 평가. 혈우병·간질환 시 연장."},
    "FIB": {"name": "Fibrinogen", "meaning": "피브리노겐", "description": "응고 단백질. 염증·출혈·간기능 이상 평가."},

    # ---------- 요화학 ----------
    "GLU_U": {"name": "Urine Glucose", "meaning": "요당", "description": "당뇨, 신세뇨관 장애 시 양성."},
    "PRO": {"name": "Urine Protein", "meaning": "요단백", "description": "단백뇨, 신장질환, 요로염 평가."},
    "SG": {"name": "Specific Gravity", "meaning": "요비중", "description": "신장의 농축능 반영."},
    "KET": {"name": "Ketones", "meaning": "케톤체", "description": "당뇨·기아·케톤산증 시 검출."},
    "BIL": {"name": "Bilirubin", "meaning": "요빌리루빈", "description": "간질환, 담즙정체 시 검출."},
    "BLO": {"name": "Blood (Hemoglobin)", "meaning": "요적혈구/혈색소", "description": "요로출혈·감염·결석 시 검출."},
    "pH_U": {"name": "Urine pH", "meaning": "요산도", "description": "산성·알칼리성 요로 환경 반영."},

    # ---------- 요침사 ----------
    "RBC_U": {"name": "RBC (Urine)", "meaning": "요적혈구", "description": "요로출혈, 감염, 결석 시 검출."},
    "WBC_U": {"name": "WBC (Urine)", "meaning": "요백혈구", "description": "요로감염, 염증 반영."},
    "Bacteria": {"name": "Bacteria", "meaning": "세균 검출", "description": "세균뇨, 감염 소견."},
    "Crystals": {"name": "Crystals", "meaning": "결정체", "description": "스트루바이트, 수산칼슘 등 결석성분 평가."}
}

