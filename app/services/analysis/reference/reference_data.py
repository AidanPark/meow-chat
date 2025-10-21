# 규칙
# - 카테고리 주석은 알파벳 순
# - 각 카테고리 내부는 code 알파벳 오름차순
# - 완전히 동일한 code만 중복 제거 (CRE/CREA, Na/Na+ 처럼 다른 표기는 유지)
# - 가능한 모든 항목에 name / unit / meaning / description 포함
# - (Ven)/(Art)/(Cap)가 코드에 포함되면 sample_type 필드를 보존

REFERENCE_TESTS = [

    # --------------------------------------------------------
    # BLOOD GAS / 혈액가스 분석
    # --------------------------------------------------------
    {"code": "AG", "name": "Anion Gap", "unit": "mmol/L", "meaning": "음이온 갭", "description": "Na⁺ + K⁺ - (Cl⁻ + HCO₃⁻) 계산값. 대사성 산증 감별에 사용."},
    {"code": "AnGap", "name": "Anion Gap", "unit": "mmol/L", "meaning": "음이온 갭", "description": "대사성 산증 감별용 계산값 (Na + K - Cl - HCO₃)."},
    {"code": "BB", "name": "Buffer Base", "unit": "mmol/L", "meaning": "완충염기량", "description": "혈중 모든 완충염기의 총합. 대사성 산·염기 불균형의 총평가 지표."},
    {"code": "BE", "name": "Base Excess", "unit": "mmol/L", "meaning": "염기 과잉(결핍) 정도", "description": "HCO₃⁻ 변화로 인한 대사성 산·염기 불균형 평가 지표."},
    {"code": "BE(Art)", "name": "Base Excess (Arterial)", "unit": "mmol/L", "meaning": "동맥혈 염기과잉", "description": "동맥혈의 대사성 불균형 정도.", "sample_type": "arterial"},
    {"code": "BE(Ven)", "name": "Base Excess (Venous)", "unit": "mmol/L", "meaning": "정맥혈 염기과잉", "description": "정맥혈의 대사성 불균형 정도.", "sample_type": "venous"},
    {"code": "BE-Ecf", "name": "Base Excess (Extracellular Fluid)", "unit": "mmol/L", "meaning": "세포외액 기준 염기과잉", "description": "세포외액 공간 기준의 대사성 산·염기 불균형 지표."},
    {"code": "COHb", "name": "Carboxyhemoglobin", "unit": "%", "meaning": "일산화탄소헤모글로빈", "description": "CO 중독 평가. 정상 <1.5%."},
    {"code": "FHHb", "name": "Deoxyhemoglobin Fraction", "unit": "%", "meaning": "탈산화헤모글로빈 분율", "description": "산소와 결합하지 않은 헤모글로빈 비율."},
    {"code": "FO2Hb", "name": "Oxyhemoglobin Fraction", "unit": "%", "meaning": "산화헤모글로빈 분율", "description": "산소와 결합한 헤모글로빈 비율."},
    {"code": "HCO3", "name": "Bicarbonate", "unit": "mmol/L", "meaning": "중탄산이온 농도", "description": "대사성 산·염기 상태를 반영. 대사성 산증 시 감소, 알칼리증 시 증가."},
    {"code": "HCO3(Art)", "name": "Bicarbonate (Arterial)", "unit": "mmol/L", "meaning": "동맥혈 중탄산이온", "description": "동맥혈의 대사성 완충능 평가.", "sample_type": "arterial"},
    {"code": "HCO3(Ven)", "name": "Bicarbonate (Venous)", "unit": "mmol/L", "meaning": "정맥혈 중탄산이온", "description": "정맥혈의 대사성 완충능.", "sample_type": "venous"},
    {"code": "HCO3-Std", "name": "Standard Bicarbonate", "unit": "mmol/L", "meaning": "표준 중탄산이온 농도", "description": "PaCO₂ 40mmHg에서의 HCO₃⁻ 농도. 대사성 산·염기 상태를 반영."},
    {"code": "iCa-pH7.4", "name": "Ionized Calcium (pH 7.4)", "unit": "mmol/L", "meaning": "pH 7.4 기준 이온화 칼슘", "description": "혈액 pH 7.4로 보정한 생리적 활성 칼슘 농도. 대사성 산증·알칼리증 평가에 사용."},
    {"code": "LAC", "name": "Lactate", "unit": "mmol/L", "meaning": "젖산 농도", "description": "저산소증, 쇼크, 대사장애 시 상승."},
    {"code": "Lac", "name": "Lactate", "unit": "mmol/L", "meaning": "젖산", "description": "저산소증, 조직관류장애 시 상승."},
    {"code": "Lac(Art)", "name": "Lactate (Arterial)", "unit": "mmol/L", "meaning": "동맥혈 젖산", "description": "동맥혈의 젖산 농도. 쇼크·저산소증 평가.", "sample_type": "arterial"},
    {"code": "Lac(Ven)", "name": "Lactate (Venous)", "unit": "mmol/L", "meaning": "정맥혈 젖산", "description": "정맥혈의 젖산 농도.", "sample_type": "venous"},
    {"code": "MetHb", "name": "Methemoglobin", "unit": "%", "meaning": "메트헤모글로빈", "description": "산소 운반 불가 형태의 Hb."},
    {"code": "O2SAT", "name": "O₂ Saturation", "unit": "%", "meaning": "혈중 산소 포화도", "description": "혈액 내 헤모글로빈의 산소 결합 정도. 저산소증 판단 지표."},
    {"code": "pCO2", "name": "Partial Pressure of CO₂", "unit": "mmHg", "meaning": "이산화탄소 분압", "description": "호흡성 산·염기 상태 평가. 상승 시 호흡저하."},
    {"code": "pCO2(Art)", "name": "Partial Pressure of CO₂ (Arterial)", "unit": "mmHg", "meaning": "동맥혈 이산화탄소 분압", "description": "동맥혈 CO₂ 농도. 호흡 기능 평가.", "sample_type": "arterial"},
    {"code": "pCO2(Ven)", "name": "Partial Pressure of CO₂ (Venous)", "unit": "mmHg", "meaning": "정맥혈 이산화탄소 분압", "description": "정맥혈 CO₂ 농도.", "sample_type": "venous"},
    {"code": "PCO2(T)", "name": "Temperature-corrected pCO₂", "unit": "mmHg", "meaning": "체온 보정된 이산화탄소 분압", "description": "환자 체온에 맞게 보정된 CO₂ 분압. 체온 상승 시 감소, 저체온 시 증가."},
    {"code": "pH", "name": "Blood pH", "unit": None, "meaning": "혈액 산도", "description": "정상 7.35-7.45. 대사성·호흡성 산·염기 상태 평가."},
    {"code": "pH(Art)", "name": "Blood pH (Arterial)", "unit": None, "meaning": "동맥혈 pH", "description": "동맥혈 산성도. 호흡/대사성 산염기 평가.", "sample_type": "arterial"},
    {"code": "pH(Ven)", "name": "Blood pH (Venous)", "unit": None, "meaning": "정맥혈 pH", "description": "정맥혈 산성도. 동맥혈보다 약간 낮음.", "sample_type": "venous"},
    {"code": "PH(T)", "name": "Temperature-corrected pH", "unit": None, "meaning": "체온 보정된 혈액 pH", "description": "환자의 체온을 반영한 pH. 체온 상승 시 감소, 저체온 시 증가."},
    {"code": "pO2", "name": "Partial Pressure of O₂", "unit": "mmHg", "meaning": "산소 분압", "description": "폐의 산소 교환 상태를 반영."},
    {"code": "pO2(Art)", "name": "Partial Pressure of O₂ (Arterial)", "unit": "mmHg", "meaning": "동맥혈 산소 분압", "description": "폐의 산소 교환 효율 평가.", "sample_type": "arterial"},
    {"code": "pO2(Ven)", "name": "Partial Pressure of O₂ (Venous)", "unit": "mmHg", "meaning": "정맥혈 산소 분압", "description": "조직의 산소 소비를 반영.", "sample_type": "venous"},
    {"code": "pO2(A-a)", "name": "Alveolar-Arterial Oxygen Gradient", "unit": "mmHg", "meaning": "폐포–동맥 산소분압차 (A-aDO₂)", "description": "폐의 산소 확산 효율을 평가하는 지표. 30mmHg 이상은 폐 확산장애 가능."},
    {"code": "PO2(T)", "name": "Temperature-corrected pO₂", "unit": "mmHg", "meaning": "체온 보정된 산소 분압", "description": "환자 체온에 맞게 보정된 O₂ 분압. 체온 상승 시 감소, 저체온 시 증가."},
    {"code": "sO2", "name": "O₂ Saturation", "unit": "%", "meaning": "산소포화도", "description": "헤모글로빈 산소결합률. 저산소증 진단에 사용."},
    {"code": "sO2(Art)", "name": "O₂ Saturation (Arterial)", "unit": "%", "meaning": "동맥혈 산소포화도", "description": "동맥혈 헤모글로빈의 산소결합률.", "sample_type": "arterial"},
    {"code": "sO2(Ven)", "name": "O₂ Saturation (Venous)", "unit": "%", "meaning": "정맥혈 산소포화도", "description": "정맥혈 헤모글로빈의 산소결합률.", "sample_type": "venous"},
    {"code": "TCO2", "name": "Total CO₂", "unit": "mmol/L", "meaning": "총 CO₂ (용존 CO₂ + HCO₃⁻)", "description": "대사성 산·염기 평가. HCO₃⁻과 거의 동일한 의미."},
    {"code": "TCO2(Art)", "name": "Total CO₂ (Arterial)", "unit": "mmol/L", "meaning": "동맥혈 총 CO₂", "description": "동맥혈의 총 탄산 함량.", "sample_type": "arterial"},
    {"code": "TCO2(Ven)", "name": "Total CO₂ (Venous)", "unit": "mmol/L", "meaning": "정맥혈 총 CO₂", "description": "정맥혈의 총 탄산 함량.", "sample_type": "venous"},
    {"code": "tHb", "name": "Total Hemoglobin", "unit": "g/dL", "meaning": "총 헤모글로빈", "description": "혈액의 산소 운반능 평가."},

    # --------------------------------------------------------
    # CBC (Complete Blood Count) / 전혈구 검사
    # --------------------------------------------------------
    {"code": "BASO", "name": "Basophils (Absolute)", "unit": "K/µL", "meaning": "호염구 절대수", "description": "희귀 항목. 알레르기·염증 반응에서 약간 증가할 수 있음."},
    {"code": "BASO%", "name": "Basophils %", "unit": "%", "meaning": "호염구 백분율", "description": "드물지만 알레르기나 만성 염증에서 약간 증가."},
    {"code": "CHr", "name": "Reticulocyte Hemoglobin Content", "unit": "pg", "meaning": "망상적혈구 헤모글로빈 함량", "description": "철 공급 상태 반영. 철결핍 시 감소."},
    {"code": "EOSIN", "name": "Eosinophils (Absolute)", "unit": "K/µL", "meaning": "호산구 절대수", "description": "기생충, 알레르기, 천식 시 증가."},
    {"code": "EOS%", "name": "Eosinophils %", "unit": "%", "meaning": "호산구 백분율", "description": "알레르기·기생충 감염 시 증가. 스테로이드 투여 시 감소."},
    {"code": "HCT", "name": "Hematocrit", "unit": "%", "meaning": "적혈구 용적률", "description": "혈액 중 적혈구가 차지하는 부피 비율. 탈수 시 증가, 빈혈 시 감소."},
    {"code": "HGB", "name": "Hemoglobin", "unit": "g/dL", "meaning": "헤모글로빈 농도", "description": "산소 운반 단백질. 빈혈 진단 기준."},
    {"code": "Lymph%", "name": "Lymphocytes %", "unit": "%", "meaning": "림프구 백분율", "description": "백혈구 중 림프구 비율. 바이러스 감염, 만성 염증 시 증가."},
    {"code": "LYMPH%", "name": "Lymphocytes %", "unit": "%", "meaning": "림프구 백분율", "description": "바이러스 감염, 만성 염증에서 증가. 스트레스 시 감소."},
    {"code": "LYMPH", "name": "Lymphocytes (Absolute)", "unit": "K/µL", "meaning": "림프구 절대수", "description": "면역반응·바이러스 감염 시 증가. 스트레스 반응 시 감소."},
    {"code": "LYM", "name": "Lymphocytes (Absolute)", "unit": "K/µL", "meaning": "림프구 절대수", "description": "면역반응·바이러스 감염 시 증가. 스트레스 반응 시 감소."},
    {"code": "LYM%", "name": "Lymphocytes %", "unit": "%", "meaning": "백혈구 중 림프구 비율", "description": "바이러스 감염, 만성 염증, 면역반응 시 증가. 스트레스 시 감소."},
    {"code": "MCH", "name": "Mean Corpuscular Hemoglobin", "unit": "pg", "meaning": "평균 적혈구 혈색소량", "description": "적혈구 1개당 헤모글로빈 함량. 철결핍성 빈혈에서 감소."},
    {"code": "MCHC", "name": "Mean Corpuscular Hemoglobin Concentration", "unit": "g/dL", "meaning": "평균 혈색소 농도", "description": "적혈구 내 Hb 농도. 저색소성 빈혈, 탈수 감별에 도움."},
    {"code": "MCV", "name": "Mean Corpuscular Volume", "unit": "fL", "meaning": "평균 적혈구 용적", "description": "적혈구 평균 크기. 거대세포빈혈(>100fL), 소세포빈혈(<80fL) 감별."},
    {"code": "MCVr", "name": "Mean Corpuscular Volume (retic)", "unit": "fL", "meaning": "망상적혈구 평균 용적", "description": "신생 적혈구 용적."},
    {"code": "MONO", "name": "Monocytes (Absolute)", "unit": "K/µL", "meaning": "단핵구 절대수", "description": "만성 감염, 조직 손상 회복기에서 증가. 골수 기능 저하 시 감소."},
    {"code": "MONO%", "name": "Monocytes %", "unit": "%", "meaning": "백혈구 중 단핵구 비율", "description": "조직 손상 회복기, 만성 염증에서 증가."},
    {"code": "NEUT", "name": "Neutrophils (Absolute)", "unit": "K/µL", "meaning": "호중구 절대수", "description": "세균 감염, 급성 염증 시 증가. 면역저하나 바이러스 감염 시 감소."},
    {"code": "NEU%", "name": "Neutrophils %", "unit": "%", "meaning": "백혈구 중 호중구 비율", "description": "세균성 염증, 급성 감염에서 증가. 면역저하·바이러스 감염 시 감소."},
    {"code": "NEU", "name": "Neutrophils (Absolute)", "unit": "K/µL", "meaning": "호중구 절대수", "description": "급성 염증, 세균 감염 시 증가. 패혈증 등에서 급감 가능."},
    {"code": "NEUTROPHILS%", "name": "Neutrophils %", "unit": "%", "meaning": "호중구 백분율 (NEU%)", "description": "백혈구 중 호중구의 비율. 세균감염, 염증 시 증가. 면역저하·바이러스 감염 시 감소."},
    {"code": "PCT", "name": "Plateletcrit", "unit": "%", "meaning": "혈소판 용적률", "description": "혈소판의 전체 혈액 부피 내 비율. 혈소판 감소증 평가에 사용."},
    {"code": "PCT%", "name": "Plateletcrit %", "unit": "%", "meaning": "혈소판 용적률 비율", "description": "전체 혈액 부피에서 혈소판이 차지하는 비율. 혈소판 감소증 평가에 사용."},
    {"code": "PDW", "name": "Platelet Distribution Width", "unit": "fL", "meaning": "혈소판 크기 분포 폭", "description": "혈소판 크기의 다양성 지표. 혈소판 생성·파괴 이상 평가에 사용."},
    {"code": "PLT", "name": "Platelets", "unit": "K/µL", "meaning": "혈소판 수", "description": "혈액응고에 관여. 감소 시 출혈 위험, 증가 시 염증 반응 가능."},
    {"code": "RBC", "name": "Red Blood Cells", "unit": "M/µL", "meaning": "적혈구 수", "description": "산소 운반 세포. 빈혈, 출혈, 탈수 평가."},
    {"code": "RDW", "name": "Red Cell Distribution Width", "unit": "%", "meaning": "적혈구 분포 폭", "description": "적혈구 크기 변동성. 재생성 빈혈·영양결핍 감별에 도움."},
    {"code": "RDW-CV", "name": "Red Cell Distribution Width (CV)", "unit": "%", "meaning": "적혈구 크기 변이계수", "description": "빈혈 감별 및 재생성 여부 평가."},
    {"code": "RDW-SD", "name": "Red Cell Distribution Width (SD)", "unit": "fL", "meaning": "적혈구 분포 폭 (표준편차)", "description": "적혈구 크기의 불균일성 정도를 나타냄. 빈혈 감별에 사용."},
    {"code": "RETIC", "name": "Reticulocyte Count", "unit": "K/µL", "meaning": "망상적혈구 수 (절대수)", "description": "적혈구 재생 정도를 반영. 재생성 빈혈에서 증가, 골수기능 저하 시 감소."},
    {"code": "RETIC-HGB", "name": "Reticulocyte Hemoglobin Content", "unit": "pg", "meaning": "망상적혈구 헤모글로빈 함량", "description": "신선한 적혈구의 철 결핍 여부 평가. 조기 철결핍 탐지 지표."},
    {"code": "RETHGB", "name": "Reticulocyte Hemoglobin Content", "unit": "pg", "meaning": "망상적혈구 Hb 함량", "description": "철공급 상태 반영; 철결핍성 빈혈 조기 지표."},
    {"code": "WBC", "name": "White Blood Cells", "unit": "K/µL", "meaning": "백혈구 수", "description": "면역반응, 염증 지표. 상승 시 감염·염증, 감소 시 골수억제."},
    {"code": "WBC-A", "name": "White Blood Cells (Analyzer variant)", "unit": "K/µL", "meaning": "장비 표기 변형 WBC", "description": "일부 장비에서 '-A' 접미로 표기."},
    {"code": "WBC-BASO", "name": "Basophils (Absolute)", "unit": "K/µL", "meaning": "호염구 절대수", "description": "희귀 항목. 알레르기·염증 반응에서 약간 증가할 수 있음."},
    {"code": "WBC-BASO%", "name": "Basophils %", "unit": "%", "meaning": "호염구 비율 (백혈구 중 호염구의 백분율)", "description": "희귀. 알레르기, 만성 염증에서 약간 증가할 수 있음."},
    {"code": "WBC-EOS", "name": "Eosinophils (Absolute)", "unit": "K/µL", "meaning": "호산구 절대수", "description": "알레르기·기생충성 질환에서 증가. 스트레스 호르몬 영향으로 감소 가능."},
    {"code": "WBC-EOS%", "name": "Eosinophils %", "unit": "%", "meaning": "호산구 비율 (백혈구 중 호산구의 백분율)", "description": "알레르기, 기생충 감염에서 증가. 스테로이드 투여 시 감소."},
    {"code": "WBC-LYM", "name": "Lymphocytes (Absolute)", "unit": "K/µL", "meaning": "림프구 절대수 (단위 부피당 세포 수)", "description": "면역활성 또는 바이러스 감염 시 증가. 스트레스, 코르티솔 상승 시 감소."},
    {"code": "WBC-LYM%", "name": "Lymphocytes %", "unit": "%", "meaning": "림프구 비율 (백혈구 중 림프구의 백분율)", "description": "바이러스 감염, 만성 염증, 면역반응 시 증가. 스트레스 시 감소."},
    {"code": "WBC-MONO", "name": "Monocytes (Absolute)", "unit": "K/µL", "meaning": "단핵구 절대수", "description": "만성 감염 또는 회복기에서 증가. 골수 기능 저하 시 감소."},
    {"code": "WBC-MONO%", "name": "Monocytes %", "unit": "%", "meaning": "단핵구 비율 (백혈구 중 단핵구의 백분율)", "description": "만성 염증, 조직 손상 후 회복기에서 증가. 골수 기능 저하 시 감소."},
    {"code": "WBC-NEU", "name": "Neutrophils (Absolute)", "unit": "K/µL", "meaning": "호중구 절대수 (단위 부피당 세포 수)", "description": "급성 염증, 세균 감염에서 크게 상승. 패혈증 등에서 급감 가능."},
    {"code": "WBC-NEU%", "name": "Neutrophils %", "unit": "%", "meaning": "호중구 비율 (백혈구 중 호중구의 백분율)", "description": "급성 염증, 세균 감염 시 증가. 면역저하·바이러스 감염 시 감소."},

    {"code": "MPV", "name": "Mean Platelet Volume", "unit": "fL", "meaning": "평균 혈소판 용적", "description": "혈소판의 평균 크기를 나타냄. 혈소판 생성 및 활성 상태 평가에 사용."},
    {"code": "Retics%", "name": "Reticulocyte Percentage", "unit": "%", "meaning": "망상적혈구 비율", "description": "혈액 내 망상적혈구의 백분율. 재생성 빈혈 평가에 사용."},
    {"code": "LYMPHO%", "name": "Lymphocytes %", "unit": "%", "meaning": "림프구 백분율", "description": "백혈구 중 림프구 비율. 바이러스성 감염, 만성 염증에서 증가할 수 있음."},
    {"code": "LYMPH", "name": "Lymphocytes (Absolute)", "unit": "K/µL", "meaning": "림프구 절대수", "description": "단위 부피당 림프구 수. 스트레스, 면역 반응 상태 평가에 활용."},

    # --------------------------------------------------------
    # CHEMISTRY / 생화학 검사
    # --------------------------------------------------------
    {"code": "A_G", "name": "Albumin/Globulin Ratio", "unit": None, "meaning": "알부민/글로불린 비율", "description": "A/G < 0.6 은 염증, 간질환, 단백소실 가능성을 시사."},
    {"code": "ALB", "name": "Albumin", "unit": "g/dL", "meaning": "알부민", "description": "간 합성 단백; 삼투압 유지."},
    {"code": "Albumin", "name": "Albumin", "unit": "g/dL", "meaning": "알부민 (Albumin)", "description": "혈장 내 주요 단백질. 간 합성 기능 및 삼투압 유지에 중요. 간부전, 신증후군 시 감소."},
    {"code": "ALP", "name": "Alkaline Phosphatase", "unit": "U/L", "meaning": "알칼리성 인산분해효소", "description": "담즙정체, 유도효소 상승."},
    {"code": "ALT", "name": "Alanine Aminotransferase", "unit": "U/L", "meaning": "간세포 효소", "description": "간세포 손상 시 상승."},
    {"code": "AST", "name": "Aspartate Aminotransferase", "unit": "U/L", "meaning": "간/근육 효소", "description": "간세포/근육 손상."},
    {"code": "BA", "name": "Bile Acids", "unit": "µmol/L", "meaning": "담즙산 (간 기능 지표)", "description": "간의 담즙 배설·재흡수 반영. 문맥전신단락, 간부전 평가에 사용."},
    {"code": "BIL-Total", "name": "Bilirubin, Total", "unit": "mg/dL", "meaning": "총 빌리루빈", "description": "간세포 손상/담즙정체."},
    {"code": "BUN", "name": "Blood Urea Nitrogen", "unit": "mg/dL", "meaning": "혈중 요소질소 (신장 기능 지표)", "description": "단백질 대사 산물로, 신장 배설 기능 반영. 탈수·신부전·GI 출혈 시 상승."},
    {"code": "BUN/CRE", "name": "BUN/Creatinine Ratio", "unit": None, "meaning": "요소질소/크레아티닌 비율", "description": "신기능·수분상태 보조지표."},
    {"code": "Ca", "name": "Calcium", "unit": "mg/dL", "meaning": "혈중 칼슘 농도", "description": "뼈·신경·근육 기능에 필수. 고칼슘혈증은 종양, 저칼슘혈증은 경련 유발."},
    {"code": "Ca++", "name": "Ionized Calcium", "unit": "mmol/L", "meaning": "이온화 칼슘", "description": "활성 형태 Ca²⁺ 농도."},
    {"code": "CHOL", "name": "Cholesterol", "unit": "mg/dL", "meaning": "총 콜레스테롤", "description": "지질대사/담즙정체."},
    {"code": "CHOL_HDL_RATIO", "name": "Cholesterol/HDL Ratio", "unit": None, "meaning": "총콜레스테롤/HDL 비율", "description": "지질 대사 균형 평가 지표. 높을수록 심혈관 위험 증가."},
    {"code": "CK", "name": "Creatine Kinase", "unit": "U/L", "meaning": "근육효소", "description": "근손상 지표."},
    {"code": "Cl-", "name": "Chloride", "unit": "mEq/L", "meaning": "혈중 염소이온 농도", "description": "전해질 균형 반영. 구토 시 감소, 산증 보상 시 증가."},
    {"code": "CPK", "name": "Creatine Phosphokinase", "unit": "U/L", "meaning": "근육 손상 효소", "description": "골격근·심근 손상 시 상승. 발작, 근육 외상에서도 증가."},
    {"code": "CRE", "name": "Creatinine", "unit": "mg/dL", "meaning": "크레아티닌", "description": "신기능 지표."},
    {"code": "CREA", "name": "Creatinine", "unit": "mg/dL", "meaning": "크레아티닌", "description": "신기능 지표 (동일 의미 변형 코드)."},
    {"code": "GGT", "name": "Gamma-Glutamyl Transferase", "unit": "U/L", "meaning": "감마-GT (간·담즙 효소)", "description": "담즙정체, 간세포 손상에서 증가. 고양이에선 민감도 낮음."},
    {"code": "GLOB", "name": "Globulin (calculated)", "unit": "g/dL", "meaning": "면역 단백질 (글로불린)", "description": "면역글로불린·급성기 단백 포함. 염증·감염 시 상승, 단백소실·간질환 시 감소."},
    {"code": "GLOB(calc)", "name": "Globulin (calculated)", "unit": "g/dL", "meaning": "글로불린 (계산값)", "description": "TP - ALB 로 계산. 면역단백 증가나 염증 상태 평가에 사용."},
    {"code": "Globulin", "name": "Globulin", "unit": "g/dL", "meaning": "글로불린", "description": "면역단백; 염증·감염에서 상승."},
    {"code": "GLU", "name": "Glucose", "unit": "mg/dL", "meaning": "혈당", "description": "에너지 대사 주요 지표. 당뇨병, 스트레스 시 상승, 패혈증·간부전 시 감소."},
    {"code": "Glu", "name": "Glucose", "unit": "mg/dL", "meaning": "포도당", "description": "혈당 수준. 당뇨·저혈당 평가."},
    {"code": "HDL_C", "name": "High-Density Lipoprotein Cholesterol", "unit": "mg/dL", "meaning": "고밀도 지질단백 콜레스테롤", "description": "좋은 콜레스테롤. 간 기능 및 지질대사 평가에 사용."},
    {"code": "IP", "name": "Inorganic Phosphorus", "unit": "mg/dL", "meaning": "무기 인산염", "description": "뼈 대사 및 신장 기능 반영. 신부전 시 상승, 부갑상선 항진 시 감소."},
    {"code": "K+", "name": "Potassium", "unit": "mEq/L", "meaning": "혈중 칼륨 농도", "description": "세포내 주요 양이온. 저칼륨혈증은 근력저하, 고칼륨혈증은 부정맥·심정지 유발."},
    {"code": "LDH", "name": "Lactate Dehydrogenase", "unit": "U/L", "meaning": "젖산탈수소효소", "description": "간·근육·심근 손상 시 상승. 비특이적 조직 손상 지표."},
    {"code": "LDL_C", "name": "Low-Density Lipoprotein Cholesterol", "unit": "mg/dL", "meaning": "저밀도 지질단백 콜레스테롤", "description": "나쁜 콜레스테롤. 고지혈증, 동맥경화 위험 지표."},
    {"code": "Mg", "name": "Magnesium", "unit": "mg/dL", "meaning": "마그네슘 농도", "description": "효소 활성 및 신경근 기능 조절. 저마그네슘혈증은 경련·부정맥 유발 가능."},
    {"code": "Na/K", "name": "Sodium/Potassium Ratio", "unit": None, "meaning": "나트륨/칼륨 비율", "description": "Na/K < 27 → Addison's disease 의심."},
    {"code": "Na_K", "name": "Sodium/Potassium Ratio", "unit": None, "meaning": "나트륨/칼륨 비율", "description": "Na/K < 27 은 Addison's disease 의심 지표로 사용."},
    {"code": "Na+", "name": "Sodium", "unit": "mEq/L", "meaning": "혈중 나트륨 농도", "description": "체액 삼투압 조절. 탈수 시 상승, 부신기능저하(Addison's) 시 감소."},
    {"code": "NH3", "name": "Ammonia", "unit": "µg/dL", "meaning": "암모니아 (간 기능 지표)", "description": "단백질 대사 부산물. 간기능 저하, 문맥전신단락에서 상승."},
    {"code": "PHOS", "name": "Phosphorus", "unit": "mg/dL", "meaning": "무기 인산염", "description": "뼈 대사 및 신장 기능 반영. 신부전 시 상승, 부갑상선 항진 시 감소."},
    {"code": "T.Billirubin", "name": "Total Bilirubin", "unit": "mg/dL", "meaning": "총 빌리루빈 (Total Bilirubin)", "description": "헤모글로빈 대사 산물. 간세포 손상, 담도 폐쇄 시 증가."},
    {"code": "T.Protein", "name": "Total Protein", "unit": "g/dL", "meaning": "총 단백질 (Total Protein)", "description": "혈장 내 단백질 농도. 알부민과 글로불린의 합. 탈수 시 증가, 간질환·단백질 손실 시 감소."},
    {"code": "T4", "name": "Total Thyroxine", "unit": "µg/dL", "meaning": "총 갑상선호르몬(T4)", "description": "갑상선 기능 평가 지표. 고양이 항진증, 개 저하증 진단에 핵심."},
    {"code": "TBIL", "name": "Total Bilirubin", "unit": "mg/dL", "meaning": "총 빌리루빈 (담즙 색소)", "description": "적혈구 파괴 및 간 배설 반영. 간질환, 용혈, 담즙정체 시 상승."},
    {"code": "TCHO", "name": "Total Cholesterol", "unit": "mg/dL", "meaning": "총 콜레스테롤", "description": "지질대사 반영. 갑상선 저하, 쿠싱증후군, 담즙정체 시 상승."},
    {"code": "TG", "name": "Triglyceride", "unit": "mg/dL", "meaning": "중성지방", "description": "지질대사 지표. 식후 상승, 당뇨·쿠싱증후군에서 증가 가능."},
    {"code": "TP", "name": "Total Protein", "unit": "g/dL", "meaning": "총 단백질 (ALB+GLOB)", "description": "혈장 내 단백질 총량. 탈수 시 상승, 단백소실·간질환 시 감소."},
    {"code": "v-AMYL", "name": "Amylase (Vet)", "unit": "U/L", "meaning": "수의전용 아밀라아제", "description": "췌장 및 장기에서 분비. 췌장염 시 상승, 신부전 시도 상승 가능."},
    {"code": "v-LIP", "name": "Lipase (Vet)", "unit": "U/L", "meaning": "수의전용 리파아제", "description": "지방분해효소. 췌장염 등에서 상승, v-AMYL보다 특이도 높음."},

    {"code": "ALKP", "name": "Alkaline Phosphatase", "unit": "U/L", "meaning": "알칼리성 인산분해효소", "description": "간, 담도, 뼈 관련 효소. 담즙 정체, 성장기, 스테로이드 영향 시 상승."},
    {"code": "AMYL", "name": "Amylase", "unit": "U/L", "meaning": "아밀라아제", "description": "췌장 및 장기에서 분비되는 소화효소. 췌장염, 신부전 시 상승."},
    {"code": "LIPA", "name": "Lipase", "unit": "U/L", "meaning": "리파아제", "description": "췌장에서 분비되는 지방분해효소. 췌장염 진단 시 AMYL과 함께 사용."},
    {"code": "AST/GOT", "name": "Aspartate Aminotransferase", "unit": "U/L", "meaning": "아스파르트산 아미노전이효소", "description": "간, 근육세포 손상 시 상승. 근육병증 감별 시 CK와 함께 해석."},
    {"code": "ALB/GLOB", "name": "Albumin/Globulin Ratio", "unit": None, "meaning": "알부민/글로불린 비율", "description": "A/G < 0.6은 염증, 간질환, 단백소실성 장질환을 시사."},
    {"code": "BUN/CREA", "name": "Blood Urea Nitrogen / Creatinine Ratio", "unit": None, "meaning": "혈중요소질소/크레아티닌 비율", "description": "신장 기능 평가에 사용. 비례 상승 시 탈수, BUN 단독 상승 시 위장출혈 가능성."},
    {"code": "Triglyceride(TG)", "name": "Triglycerides", "unit": "mg/dL", "meaning": "중성지방 농도", "description": "지질 대사 지표. 고지혈증, 당뇨, 갑상선 기능저하에서 상승."},
    {"code": "SDMA", "name": "Symmetric Dimethylarginine", "unit": "µg/dL", "meaning": "대칭성 디메틸아르기닌", "description": "조기 신장기능 저하를 감지하는 바이오마커. CREA보다 민감."},
    {"code": "Fructosamine", "name": "Fructosamine", "unit": "µmol/L", "meaning": "프럭토사민", "description": "최근 1~3주간 혈당 조절 상태를 반영. 당뇨 조절 모니터링에 사용."},
    {"code": "Lactate", "name": "Lactate", "unit": "mmol/L", "meaning": "젖산 농도", "description": "조직 저산소증, 쇼크, 대사장애 시 상승. 수액 치료 반응 모니터링에 유용."},

    # --------------------------------------------------------
    # COAGULATION / 응고 검사
    # --------------------------------------------------------
    {"code": "aPTT", "name": "Activated Partial Thromboplastin Time", "unit": "sec", "meaning": "활성화 부분 트롬보플라스틴 시간", "description": "내인성 응고경로 평가. 혈우병·간질환 시 연장."},
    {"code": "FIB", "name": "Fibrinogen", "unit": "mg/dL", "meaning": "피브리노겐", "description": "응고 단백질. 염증·출혈·간기능 이상 평가."},
    {"code": "PT", "name": "Prothrombin Time", "unit": "sec", "meaning": "프로트롬빈 시간", "description": "외인성 응고경로 평가. 비타민K 결핍, 간질환 시 연장."},

    # --------------------------------------------------------
    # IMMUNOLOGY / 면역학 검사
    # --------------------------------------------------------
    {"code": "CORT", "name": "Cortisol", "unit": "µg/dL", "meaning": "코르티솔 (부신 피질 호르몬)", "description": "쿠싱증후군·애디슨병 감별에 사용."},
    {"code": "cPL", "name": "Canine Pancreatic Lipase", "unit": "µg/L", "meaning": "개 췌장 특이 리파아제", "description": "췌장염 진단용. 개 전용 항목."},
    {"code": "CRP", "name": "C-Reactive Protein", "unit": "mg/dL", "meaning": "급성기 단백질 (염증 지표)", "description": "염증·감염·수술 후 반응성 상승. 개에서 유용, 고양이는 제한적."},
    {"code": "fPL", "name": "Feline Pancreatic Lipase", "unit": "µg/L", "meaning": "고양이 췌장 특이 리파아제", "description": "고양이 췌장염 진단용. fPL 증가 시 췌장염 의심."},
    {"code": "FSAA", "name": "Feline Serum Amyloid A", "unit": "µg/mL", "meaning": "고양이 혈청 아밀로이드 A", "description": "고양이 염증·감염의 민감한 급성기 단백질. feline-specific 염증지표."},
    {"code": "FT4", "name": "Free Thyroxine", "unit": "ng/dL", "meaning": "자유 T4 (활성형 갑상선 호르몬)", "description": "갑상선 기능 평가 시 TSH와 함께 측정."},
    {"code": "proBNP", "name": "NT-proBNP", "unit": "pmol/L", "meaning": "심근 스트레스 마커", "description": "고양이 심근비대증 등 심장질환 선별."},
    {"code": "SAA", "name": "Serum Amyloid A", "unit": "µg/mL", "meaning": "급성기 단백질 (고양이 염증 지표)", "description": "고양이 염증·감염 시 민감하게 상승. CRP보다 feline-specific."},
    {"code": "SAA-Vcheck", "name": "Serum Amyloid A (Vcheck)", "unit": "µg/mL", "meaning": "급성기 단백질", "description": "Vcheck 플랫폼의 SAA."},
    {"code": "TSH", "name": "Thyroid Stimulating Hormone", "unit": "ng/mL", "meaning": "갑상선 자극 호르몬", "description": "개의 갑상선 기능 저하증 평가에 사용."},

    # --------------------------------------------------------
    # URINE / 요검사
    # --------------------------------------------------------
    {"code": "Bacteria", "name": "Bacteria", "unit": None, "meaning": "세균 검출", "description": "세균뇨, 감염 소견."},
    {"code": "BIL", "name": "Bilirubin", "unit": "mg/dL", "meaning": "요빌리루빈", "description": "간질환, 담즙정체 시 검출."},
    {"code": "BLO", "name": "Blood (Hemoglobin)", "unit": None, "meaning": "요적혈구/혈색소", "description": "요로출혈·감염·결석 시 검출."},
    {"code": "Crystals", "name": "Crystals", "unit": None, "meaning": "결정체", "description": "스트루바이트, 수산칼슘 등 결석성분 평가."},
    {"code": "GLU_U", "name": "Urine Glucose", "unit": "mg/dL", "meaning": "요당", "description": "당뇨, 신세뇨관 장애 시 양성."},
    {"code": "KET", "name": "Ketones", "unit": "mg/dL", "meaning": "케톤체", "description": "당뇨·기아·케톤산증 시 검출."},
    {"code": "pH_U", "name": "Urine pH", "unit": None, "meaning": "요산도", "description": "산성·알칼리성 요로 환경 반영."},
    {"code": "PRO", "name": "Urine Protein", "unit": "mg/dL", "meaning": "요단백", "description": "단백뇨, 신장질환, 요로염 평가."},
    {"code": "RBC_U", "name": "RBC (Urine)", "unit": "/hpf", "meaning": "요적혈구", "description": "요로출혈, 감염, 결석 시 검출."},
    {"code": "SG", "name": "Specific Gravity", "unit": None, "meaning": "요비중", "description": "신장의 농축능 반영."},
    {"code": "WBC_U", "name": "WBC (Urine)", "unit": "/hpf", "meaning": "요백혈구", "description": "요로감염, 염증 반영."},

    # --------------------------------------------------------
    # ENDOCRINE / SPECIAL TESTS (내분비 및 특수검사)
    # --------------------------------------------------------
    {"code": "Heartworm Ag", "name": "Heartworm Antigen Test", "unit": "Positive/Negative", "meaning": "심장사상충 항원 검사", "description": "Dirofilaria immitis 성충 항원 검출. 감염 여부 확인용."},
    {"code": "FeLV", "name": "Feline Leukemia Virus Antigen", "unit": "Positive/Negative", "meaning": "고양이 백혈병바이러스 항원 검사", "description": "FeLV 감염 여부를 진단. 고양이 만성질환의 주요 감별항목."},
    {"code": "FIV", "name": "Feline Immunodeficiency Virus Antibody", "unit": "Positive/Negative", "meaning": "고양이 면역결핍바이러스 항체 검사", "description": "FIV 감염 여부를 확인. 면역저하 질환 감별에 사용."},

    # --------------------------------------------------------
    # OTHER / 기타
    # --------------------------------------------------------
    {"code": "BP", "name": "Blood Pressure", "unit": "mmHg", "meaning": "혈압", "description": "수축기/이완기/평균혈압(MAP) 포함 가능."},
]

__all__ = ['REFERENCE_TESTS']