# ============================================================
# CBC, 혈액가스, 단백질, 전해질 등 서브파라미터 표준 정의
# ============================================================

SUBPARAMETERS = {

    # --------------------------------------------------------
    # CBC (Complete Blood Count)
    # --------------------------------------------------------
    "CBC": [
        {
            "code": "WBC-NEU%",
            "name": "Neutrophils %",
            "unit": "%",
            "meaning": "호중구 비율 (백혈구 중 호중구의 백분율)",
            "description": "급성 염증, 세균 감염 시 증가. 면역저하·바이러스 감염 시 감소."
        },
        {
            "code": "WBC-LYM%",
            "name": "Lymphocytes %",
            "unit": "%",
            "meaning": "림프구 비율 (백혈구 중 림프구의 백분율)",
            "description": "바이러스 감염, 만성 염증, 면역반응 시 증가. 스트레스 시 감소."
        },
        {
            "code": "WBC-MONO%",
            "name": "Monocytes %",
            "unit": "%",
            "meaning": "단핵구 비율 (백혈구 중 단핵구의 백분율)",
            "description": "만성 염증, 조직 손상 후 회복기에서 증가. 골수 기능 저하 시 감소."
        },
        {
            "code": "WBC-EOS%",
            "name": "Eosinophils %",
            "unit": "%",
            "meaning": "호산구 비율 (백혈구 중 호산구의 백분율)",
            "description": "알레르기, 기생충 감염에서 증가. 스테로이드 투여 시 감소."
        },
        {
            "code": "WBC-BASO%",
            "name": "Basophils %",
            "unit": "%",
            "meaning": "호염구 비율 (백혈구 중 호염구의 백분율)",
            "description": "희귀. 알레르기, 만성 염증에서 약간 증가할 수 있음."
        },
        {
            "code": "WBC-NEU#",
            "name": "Neutrophils (Absolute)",
            "unit": "10³/µL",
            "meaning": "호중구 절대수 (단위 부피당 세포 수)",
            "description": "급성 염증, 세균 감염에서 크게 상승. 패혈증 등에서 급감 가능."
        },
        {
            "code": "WBC-LYM#",
            "name": "Lymphocytes (Absolute)",
            "unit": "10³/µL",
            "meaning": "림프구 절대수 (단위 부피당 세포 수)",
            "description": "면역활성 또는 바이러스 감염 시 증가. 스트레스, 코르티솔 상승 시 감소."
        },
        {
            "code": "WBC-MONO#",
            "name": "Monocytes (Absolute)",
            "unit": "10³/µL",
            "meaning": "단핵구 절대수",
            "description": "만성 감염 또는 회복기에서 증가. 골수 기능 저하 시 감소."
        },
        {
            "code": "WBC-EOS#",
            "name": "Eosinophils (Absolute)",
            "unit": "10³/µL",
            "meaning": "호산구 절대수",
            "description": "알레르기·기생충성 질환에서 증가. 스트레스 호르몬 영향으로 감소 가능."
        },
        {
            "code": "WBC-BASO#",
            "name": "Basophils (Absolute)",
            "unit": "10³/µL",
            "meaning": "호염구 절대수",
            "description": "희귀 항목. 알레르기·염증 반응에서 약간 증가할 수 있음."
        }
    ],

    # --------------------------------------------------------
    # CBC (Complete Blood Count) - 비 WBC 접두형 세부항목
    # --------------------------------------------------------
    "CBC_BASIC": [
        {
            "code": "NEU%",
            "name": "Neutrophils %",
            "unit": "%",
            "meaning": "백혈구 중 호중구 비율",
            "description": "세균성 염증, 급성 감염에서 증가. 면역저하·바이러스 감염 시 감소."
        },
        {
            "code": "LYM%",
            "name": "Lymphocytes %",
            "unit": "%",
            "meaning": "백혈구 중 림프구 비율",
            "description": "바이러스 감염, 만성 염증에서 증가. 스트레스 시 감소."
        },
        {
            "code": "MONO%",
            "name": "Monocytes %",
            "unit": "%",
            "meaning": "백혈구 중 단핵구 비율",
            "description": "조직 손상 회복기, 만성 염증에서 증가."
        },
        {
            "code": "EOS%",
            "name": "Eosinophils %",
            "unit": "%",
            "meaning": "백혈구 중 호산구 비율",
            "description": "알레르기·기생충 감염 시 증가. 스테로이드 투여 시 감소."
        },
        {
            "code": "BASO%",
            "name": "Basophils %",
            "unit": "%",
            "meaning": "백혈구 중 호염구 비율",
            "description": "드물지만 알레르기나 만성 염증에서 약간 증가."
        },
        {
            "code": "NEU#",
            "name": "Neutrophils (Absolute)",
            "unit": "10³/µL",
            "meaning": "호중구 절대수",
            "description": "급성 염증, 세균 감염 시 증가. 패혈증 등에서 급감 가능."
        },
        {
            "code": "LYM#",
            "name": "Lymphocytes (Absolute)",
            "unit": "10³/µL",
            "meaning": "림프구 절대수",
            "description": "면역활성, 바이러스 감염 시 증가. 스트레스 반응 시 감소."
        },
        {
            "code": "MONO#",
            "name": "Monocytes (Absolute)",
            "unit": "10³/µL",
            "meaning": "단핵구 절대수",
            "description": "만성 염증, 회복기에서 증가. 골수 기능 저하 시 감소."
        },
        {
            "code": "EOS#",
            "name": "Eosinophils (Absolute)",
            "unit": "10³/µL",
            "meaning": "호산구 절대수",
            "description": "알레르기·기생충 질환에서 증가. 스트레스 호르몬 영향으로 감소 가능."
        },
        {
            "code": "BASO#",
            "name": "Basophils (Absolute)",
            "unit": "10³/µL",
            "meaning": "호염구 절대수",
            "description": "희귀 항목. 알레르기·염증 반응에서 약간 증가할 수 있음."
        },
        {
            "code": "RDW-CV",
            "name": "Red Cell Distribution Width (CV)",
            "unit": "%",
            "meaning": "적혈구 분포 폭 (변이계수)",
            "description": "적혈구 크기의 불균일성 지표. 빈혈 감별에 사용."
        },
        {
            "code": "RETIC-HGB",
            "name": "Reticulocyte Hemoglobin Content",
            "unit": "pg",
            "meaning": "망상적혈구 헤모글로빈 함량",
            "description": "신선한 적혈구의 철 결핍 여부 평가. 조기 철결핍 탐지 지표."
        },
        {
            "code": "PCT",
            "name": "Plateletcrit",
            "unit": "%",
            "meaning": "혈소판 용적률",
            "description": "혈소판의 전체 혈액 부피 내 비율. 혈소판 감소증 평가에 사용."
        },
        {
            "code": "RETIC",
            "name": "Reticulocyte Count",
            "unit": "10³/µL",
            "meaning": "망상적혈구 수 (절대수)",
            "description": "적혈구 재생 정도를 반영. 재생성 빈혈에서 증가, 골수기능 저하 시 감소."
        },
        {
            "code": "NEUTROPHILS(%)",
            "name": "Neutrophils %",
            "unit": "%",
            "meaning": "호중구 백분율 (NEU%)",
            "description": "백혈구 중 호중구의 비율. 세균감염, 염증 시 증가. 면역저하·바이러스 감염 시 감소."
        },
        {
            "code": "Lymph#",
            "name": "Lymphocytes (Absolute)",
            "unit": "10³/µL",
            "meaning": "림프구 절대수 (Lymphocyte #)",
            "description": "면역활성, 바이러스 감염 시 증가. 스트레스, 코르티솔 상승 시 감소."
        },
        {
            "code": "GRAN#",
            "name": "Granulocytes (Absolute)",
            "unit": "10³/µL",
            "meaning": "과립구 절대수 (호중구+호산구+호염구)",
            "description": "세균감염, 염증 반응 시 증가. 골수 억제나 면역저하 시 감소."
        },
        {
            "code": "Lymph%",
            "name": "Lymphocytes %",
            "unit": "%",
            "meaning": "림프구 백분율",
            "description": "백혈구 중 림프구 비율. 바이러스 감염, 만성 염증 시 증가."
        },
        {
            "code": "PCT%",
            "name": "Plateletcrit %",
            "unit": "%",
            "meaning": "혈소판 용적률 비율",
            "description": "전체 혈액 부피에서 혈소판이 차지하는 비율. 혈소판 감소증 평가에 사용."
        },
        {
            "code": "PDW",
            "name": "Platelet Distribution Width",
            "unit": "fL",
            "meaning": "혈소판 크기 분포 폭",
            "description": "혈소판 크기의 다양성 지표. 혈소판 생성·파괴 이상 평가에 사용."
        },
        {
            "code": "RDW-SD",
            "name": "Red Cell Distribution Width (SD)",
            "unit": "fL",
            "meaning": "적혈구 분포 폭 (표준편차)",
            "description": "적혈구 크기의 불균일성 정도를 나타냄. 빈혈 감별에 사용."
        },
        {
            "code": "RETHGB",
            "name": "Reticulocyte Hemoglobin Content",
            "unit": "pg",
            "meaning": "망상적혈구 헤모글로빈 함량",
            "description": "신생 적혈구(망상적혈구)의 평균 헤모글로빈 함량을 반영. 철 결핍 여부와 조혈 상태를 평가하는 지표."
        },
        {
            "code": "LYMPHO(%)",
            "name": "Lymphocytes %",
            "unit": "%",
            "meaning": "림프구 백분율",
            "description": "백혈구 중 림프구의 비율. 바이러스 감염, 만성 염증, 면역반응 시 증가."
        },
        {
            "code": "Mono(%)",
            "name": "Monocytes %",
            "unit": "%",
            "meaning": "단핵구 백분율",
            "description": "백혈구 중 단핵구의 비율. 만성 염증, 조직 손상 회복기에서 증가."
        },
        {
            "code": "EOS(%)",
            "name": "Eosinophils %",
            "unit": "%",
            "meaning": "호산구 백분율",
            "description": "알레르기, 기생충 감염에서 증가. 스테로이드 투여 시 감소."
        },
        {
            "code": "BASO(%)",
            "name": "Basophils %",
            "unit": "%",
            "meaning": "호염구 백분율",
            "description": "희귀 항목. 알레르기, 만성 염증에서 약간 증가할 수 있음."
        },
        {
            "code": "NEUT",
            "name": "Neutrophils (Absolute)",
            "unit": "10³/µL",
            "meaning": "호중구 절대수",
            "description": "세균 감염, 급성 염증 시 증가. 면역저하나 바이러스 감염 시 감소."
        },
        {
            "code": "LYMPH",
            "name": "Lymphocytes (Absolute)",
            "unit": "10³/µL",
            "meaning": "림프구 절대수",
            "description": "면역 활성화, 바이러스 감염 시 증가. 스트레스, 코르티솔 상승 시 감소."
        },
        {
            "code": "MONO",
            "name": "Monocytes (Absolute)",
            "unit": "10³/µL",
            "meaning": "단핵구 절대수",
            "description": "만성 감염, 조직 손상 회복기에서 증가. 골수 기능 저하 시 감소."
        },
        {
            "code": "BASO",
            "name": "Basophils (Absolute)",
            "unit": "10³/µL",
            "meaning": "호염구 절대수",
            "description": "희귀 항목. 알레르기, 기생충 감염 등에서 약간 증가할 수 있음."
        },
    ],

    # --------------------------------------------------------
    # IMMUNOLOGY (면역 및 특수검사)
    # --------------------------------------------------------
    "IMMUNOLOGY": [
        {
            "code": "CRP",
            "name": "C-Reactive Protein",
            "unit": "mg/dL",
            "meaning": "급성기 단백질 (염증 지표)",
            "description": "염증·감염·수술 후 반응성 상승. 개에서 유용, 고양이는 제한적."
        },
        {
            "code": "SAA",
            "name": "Serum Amyloid A",
            "unit": "µg/mL",
            "meaning": "급성기 단백질 (고양이 염증 지표)",
            "description": "고양이 염증·감염 시 민감하게 상승. CRP보다 feline-specific."
        },
        {
            "code": "cPL",
            "name": "Canine Pancreatic Lipase",
            "unit": "µg/L",
            "meaning": "개 췌장 특이 리파아제",
            "description": "췌장염 진단용. 개 전용 항목."
        },
        {
            "code": "fPL",
            "name": "Feline Pancreatic Lipase",
            "unit": "µg/L",
            "meaning": "고양이 췌장 특이 리파아제",
            "description": "고양이 췌장염 진단용. fPL 증가 시 췌장염 의심."
        },
        {
            "code": "TSH",
            "name": "Thyroid Stimulating Hormone",
            "unit": "ng/mL",
            "meaning": "갑상선 자극 호르몬",
            "description": "개의 갑상선 기능 저하증 평가에 사용."
        },
        {
            "code": "FT4",
            "name": "Free Thyroxine",
            "unit": "ng/dL",
            "meaning": "자유 T4 (활성형 갑상선 호르몬)",
            "description": "갑상선 기능 평가 시 TSH와 함께 측정."
        },
        {
            "code": "CORT",
            "name": "Cortisol",
            "unit": "µg/dL",
            "meaning": "코르티솔 (부신 피질 호르몬)",
            "description": "쿠싱증후군·애디슨병 감별에 사용."
        },
        {
            "code": "FSAA",
            "name": "Feline Serum Amyloid A",
            "unit": "µg/mL",
            "meaning": "고양이 혈청 아밀로이드 A",
            "description": "고양이 염증·감염의 민감한 급성기 단백질. feline-specific 염증지표."
        }
    ], 

    # --------------------------------------------------------
    # COAGULATION (혈액응고 검사)
    # --------------------------------------------------------
    "COAGULATION": [
        {
            "code": "PT",
            "name": "Prothrombin Time",
            "unit": "sec",
            "meaning": "프로트롬빈 시간",
            "description": "외인성 응고경로 평가. 비타민K 결핍, 간질환 시 연장."
        },
        {
            "code": "aPTT",
            "name": "Activated Partial Thromboplastin Time",
            "unit": "sec",
            "meaning": "활성화 부분 트롬보플라스틴 시간",
            "description": "내인성 응고경로 평가. 혈우병·간질환 시 연장."
        },
        {
            "code": "FIB",
            "name": "Fibrinogen",
            "unit": "mg/dL",
            "meaning": "피브리노겐",
            "description": "응고 단백질. 염증·출혈·간기능 이상 평가."
        }
    ],

    # --------------------------------------------------------
    # BLOOD GAS (혈액가스 분석)
    # --------------------------------------------------------
    "BLOOD_GAS": [
        {
            "code": "HCO3",
            "name": "Bicarbonate",
            "unit": "mmol/L",
            "meaning": "중탄산이온 농도",
            "description": "대사성 산·염기 상태를 반영. 대사성 산증 시 감소, 알칼리증 시 증가."
        },
        {
            "code": "BE",
            "name": "Base Excess",
            "unit": "mmol/L",
            "meaning": "염기 과잉(결핍) 정도",
            "description": "HCO₃⁻ 변화로 인한 대사성 산·염기 불균형 평가 지표."
        },
        {
            "code": "TCO2",
            "name": "Total CO₂",
            "unit": "mmol/L",
            "meaning": "총 CO₂ (용존 CO₂ + HCO₃⁻)",
            "description": "대사성 산·염기 평가. HCO₃⁻과 거의 동일한 의미."
        },
        {
            "code": "O2SAT",
            "name": "O₂ Saturation",
            "unit": "%",
            "meaning": "혈중 산소 포화도",
            "description": "혈액 내 헤모글로빈의 산소 결합 정도. 저산소증 판단 지표."
        },
        {
            "code": "AG",
            "name": "Anion Gap",
            "unit": "mmol/L",
            "meaning": "음이온 갭",
            "description": "Na⁺ + K⁺ - (Cl⁻ + HCO₃⁻) 계산값. 대사성 산증 감별에 사용."
        },
        {
            "code": "pCO2",
            "name": "Partial Pressure of CO₂",
            "unit": "mmHg",
            "meaning": "이산화탄소 분압",
            "description": "호흡성 산·염기 상태 평가. 상승 시 호흡저하."
        },
        {
            "code": "pO2",
            "name": "Partial Pressure of O₂",
            "unit": "mmHg",
            "meaning": "산소 분압",
            "description": "폐의 산소 교환 상태를 반영."
        },
        {
            "code": "sO2",
            "name": "O₂ Saturation",
            "unit": "%",
            "meaning": "산소포화도",
            "description": "헤모글로빈 산소결합률. 저산소증 진단에 사용."
        },
        {
            "code": "tHb",
            "name": "Total Hemoglobin",
            "unit": "g/dL",
            "meaning": "총 헤모글로빈",
            "description": "혈액의 산소 운반능 평가."
        },
        {
            "code": "AnGap",
            "name": "Anion Gap",
            "unit": "mmol/L",
            "meaning": "음이온 갭",
            "description": "대사성 산증 감별용 계산값 (Na + K - Cl - HCO₃)."
        },
        {
            "code": "PH(T)",
            "name": "Temperature-corrected pH",
            "unit": "",
            "meaning": "체온 보정된 혈액 pH",
            "description": "환자의 체온을 반영한 pH. 체온 상승 시 감소, 저체온 시 증가."
        },
        {
            "code": "PCO2(T)",
            "name": "Temperature-corrected pCO₂",
            "unit": "mmHg",
            "meaning": "체온 보정된 이산화탄소 분압",
            "description": "환자 체온에 맞게 보정된 CO₂ 분압. 체온 상승 시 감소, 저체온 시 증가."
        },
        {
            "code": "PO2(T)",
            "name": "Temperature-corrected pO₂",
            "unit": "mmHg",
            "meaning": "체온 보정된 산소 분압",
            "description": "환자 체온에 맞게 보정된 O₂ 분압. 체온 상승 시 감소, 저체온 시 증가."
        },
        {
            "code": "pO2(A-a)",
            "name": "Alveolar-Arterial Oxygen Gradient",
            "unit": "mmHg",
            "meaning": "폐포–동맥 산소분압차 (A-aDO₂)",
            "description": "폐의 산소 확산 효율을 평가하는 지표. 30mmHg 이상은 폐 확산장애 가능."
        },
        {
            "code": "HCO3-Std",
            "name": "Standard Bicarbonate",
            "unit": "mmol/L",
            "meaning": "표준 중탄산이온 농도",
            "description": "PaCO₂ 40mmHg에서의 HCO₃⁻ 농도. 대사성 산·염기 상태를 반영."
        },
        {
            "code": "BB",
            "name": "Buffer Base",
            "unit": "mmol/L",
            "meaning": "완충염기량",
            "description": "혈중 모든 완충염기의 총합. 대사성 산·염기 불균형의 총평가 지표."
        },
        {
            "code": "BE-Ecf",
            "name": "Base Excess (Extracellular Fluid)",
            "unit": "mmol/L",
            "meaning": "세포외액 기준 염기과잉",
            "description": "세포외액 공간 기준의 대사성 산·염기 불균형 지표."
        }  
    ],

    # --------------------------------------------------------
    # PROTEIN PROFILE (단백질 관련 계산값)
    # --------------------------------------------------------
    "PROTEIN_PROFILE": [
        {
            "code": "GLOB(calc)",
            "name": "Globulin (calculated)",
            "unit": "g/dL",
            "meaning": "글로불린 (계산값)",
            "description": "TP - ALB 로 계산. 면역단백 증가나 염증 상태 평가에 사용."
        },
        {
            "code": "A_G",
            "name": "Albumin/Globulin Ratio",
            "unit": None,
            "meaning": "알부민/글로불린 비율",
            "description": "A/G < 0.6 은 염증, 간질환, 단백소실 가능성을 시사."
        },
        {
            "code": "T.Protein",
            "name": "Total Protein",
            "unit": "g/dL",
            "meaning": "총 단백질 (Total Protein)",
            "description": "혈장 내 단백질 농도. 알부민과 글로불린의 합. 탈수 시 증가, 간질환·단백질 손실 시 감소."
        },
        {
            "code": "Albumin",
            "name": "Albumin",
            "unit": "g/dL",
            "meaning": "알부민 (Albumin)",
            "description": "혈장 내 주요 단백질. 간 합성 기능 및 삼투압 유지에 중요. 간부전, 신증후군 시 감소."
        },
        {
            "code": "Globulin",
            "name": "Globulin",
            "unit": "g/dL",
            "meaning": "글로불린 (Globulin)",
            "description": "면역글로불린 및 급성기 단백질. 염증, 면역반응, 감염 시 증가."
        },
        {
            "code": "T.Billirubin",
            "name": "Total Bilirubin",
            "unit": "mg/dL",
            "meaning": "총 빌리루빈 (Total Bilirubin)",
            "description": "헤모글로빈 대사 산물. 간세포 손상, 담도 폐쇄 시 증가."
        },
    ],

    # --------------------------------------------------------
    # ELECTROLYTE RATIO (전해질 관련 계산값)
    # --------------------------------------------------------
    "ELECTROLYTE_RATIO": [
        {
            "code": "Na_K",
            "name": "Sodium/Potassium Ratio",
            "unit": None,
            "meaning": "나트륨/칼륨 비율",
            "description": "Na/K < 27 은 Addison's disease 의심 지표로 사용."
        },
        {
            "code": "iCa-pH7.4",
            "name": "Ionized Calcium (pH 7.4)",
            "unit": "mmol/L",
            "meaning": "pH 7.4 기준 이온화 칼슘",
            "description": "혈액 pH 7.4로 보정한 생리적 활성 칼슘 농도. 대사성 산증·알칼리증 평가에 사용."
        },
        {
            "code": "Na/K",
            "name": "Sodium/Potassium Ratio",
            "unit": None,
            "meaning": "나트륨/칼륨 비율",
            "description": "전해질 균형을 반영. Na/K < 27 은 Addison’s disease(부신피질 기능저하) 의심 지표."
        },
    ],

    # --------------------------------------------------------
    # LIPID PROFILE (지질 관련 계산값)
    # --------------------------------------------------------
    "LIPID_PROFILE": [
        {
            "code": "HDL_C",
            "name": "High-Density Lipoprotein Cholesterol",
            "unit": "mg/dL",
            "meaning": "고밀도 지질단백 콜레스테롤",
            "description": "좋은 콜레스테롤. 간 기능 및 지질대사 평가에 사용."
        },
        {
            "code": "LDL_C",
            "name": "Low-Density Lipoprotein Cholesterol",
            "unit": "mg/dL",
            "meaning": "저밀도 지질단백 콜레스테롤",
            "description": "나쁜 콜레스테롤. 고지혈증, 동맥경화 위험 지표."
        },
        {
            "code": "CHOL_HDL_RATIO",
            "name": "Cholesterol/HDL Ratio",
            "unit": None,
            "meaning": "총콜레스테롤/HDL 비율",
            "description": "지질 대사 균형 평가 지표. 높을수록 심혈관 위험 증가."
        }
    ],

    # --------------------------------------------------------
    # DERIVED RATIOS (계산/비율 항목)
    # --------------------------------------------------------
    "DERIVED_RATIOS": [
        {
            "code": "BUN_CREA",
            "name": "BUN/Creatinine Ratio",
            "unit": None,
            "meaning": "BUN/크레아티닌 비율",
            "description": "탈수, 신부전, 출혈성 질환 평가 지표."
        },
        {
            "code": "A_G(calc)",
            "name": "Albumin/Globulin Ratio (calc)",
            "unit": None,
            "meaning": "알부민/글로불린 비율 (계산값)",
            "description": "단백대사 이상, 염증성 질환 감별에 사용."
        },
        {
            "code": "ALB_GLOB",
            "name": "Albumin/Globulin Ratio",
            "unit": None,
            "meaning": "단백비",
            "description": "염증, 간질환, 단백소실 감별에 사용."
        },
        {
            "code": "BUN/CRE",
            "name": "BUN/Creatinine Ratio",
            "unit": None,
            "meaning": "요소질소/크레아티닌 비율",
            "description": "신기능 평가 보조 지표. 탈수나 GI 출혈 시 상승, 간부전 시 감소."
        },
    ]    
}
