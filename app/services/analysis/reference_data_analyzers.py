# ============================================================
# 각 제조사별 분석기 정보
# ============================================================

ANALYZERS = {
	  "Abaxis": {
	
		"VetScan VS2": {
            "info": {
                "type": "혈청화학 분석기 (Clinical Chemistry Analyzer)",
                "release": "VetScan VS2 (2nd Gen)",
                "method": "로터 기반 화학 분석 (건식/습식 혼합)",
                "target": "개, 고양이, 소형동물",
                "features": "로터 카트리지 기반, 약 12분 내 결과, 다양한 프로필",
                "integration": "Abaxis Data Manager / VetScan Cloud",
                "market": "소형 동물병원에서 널리 사용되는 POC 화학 분석기",
                "notes": "레퍼런스 인터벌은 가이드이며, 최종 기준은 병원/개체군에서 확립해야 함."
            },
		  "tests": [
			{"code":"ALB","name":"Albumin","unit":"g/dL",
			 "reference_range":{"dog":"2.5-4.4","cat":"2.2-4.4"}},
			{"code":"ALKP","name":"Alkaline Phosphatase","unit":"U/L",
			 "reference_range":{"dog":"20-150","cat":"10-90"}},
			{"code":"ALT","name":"Alanine Aminotransferase","unit":"U/L",
			 "reference_range":{"dog":"10-118","cat":"20-100"}},
			{"code":"AMY","name":"Amylase","unit":"U/L",
			 "reference_range":{"dog":"200-1200","cat":"300-1100"}},
			{"code":"AST","name":"Aspartate Aminotransferase","unit":"U/L",
			 "reference_range":{"dog":"14-45","cat":"12-43"}},
			{"code":"BA","name":"Bile Acids","unit":"µmol/L",
			 "reference_range":{"dog":"Fasting:1-4 (2h:≤25)","cat":"Fasting:1-3 (2h:≤25)"}},
			{"code":"BUN","name":"Blood Urea Nitrogen","unit":"mg/dL",
			 "reference_range":{"dog":"7-25","cat":"10-30"}},
			{"code":"Ca","name":"Calcium","unit":"mg/dL",
			 "reference_range":{"dog":"8.6-11.8","cat":"8.0-11.8"}},
			{"code":"CHOL","name":"Cholesterol","unit":"mg/dL",
			 "reference_range":{"dog":"125-270","cat":"90-205"}},
			{"code":"CK","name":"Creatine Kinase","unit":"U/L",
			 "reference_range":{"dog":"Not established","cat":"Not established"}},  # 표에 canine/feline 공통단위 값 미기재
			{"code":"Cl-","name":"Chloride","unit":"mmol/L",
			 "reference_range":{"dog":"106-120","cat":"112-126"}},
			{"code":"CRE","name":"Creatinine","unit":"mg/dL",
			 "reference_range":{"dog":"0.3-1.4","cat":"0.3-2.1"}},
			{"code":"GGT","name":"Gamma-Glutamyl Transferase","unit":"U/L",
			 "reference_range":{"dog":"0-7","cat":"0-2"}},
			{"code":"GLOB","name":"Globulin (calculated)","unit":"g/dL",
			 "reference_range":{"dog":"3.2-5.2","cat":"1.5-5.7"},
			 "notes":"일부 종(조류 등)은 보정식 필요(원문 주석 'GLOB*')."},
			{"code":"GLU","name":"Glucose","unit":"mg/dL",
			 "reference_range":{"dog":"60-110","cat":"70-150"}},
			{"code":"K+","name":"Potassium","unit":"mmol/L",
			 "reference_range":{"dog":"3.7-5.8","cat":"2.5-5.2"}},
			{"code":"Mg","name":"Magnesium","unit":"mg/dL",
			 "reference_range":{"dog":"Not established","cat":"Not established"}},
			{"code":"Na+","name":"Sodium","unit":"mmol/L",
			 "reference_range":{"dog":"138-160","cat":"142-164"}},
			{"code":"PHOS","name":"Phosphorus","unit":"mg/dL",
			 "reference_range":{"dog":"2.5-6.8","cat":"3.5-8.5"}},
			{"code":"T4","name":"Total Thyroxine","unit":"µg/dL",
			 "reference_range":{"dog":"1.1-4.0","cat":"1.5-4.8"}},
			{"code":"TBIL","name":"Total Bilirubin","unit":"mg/dL",
			 "reference_range":{"dog":"0.1-0.5","cat":"0.5-0.6"}},
			{"code":"tCO2","name":"Total CO2","unit":"mmol/L",
			 "reference_range":{"dog":"12-27","cat":"15-24"}},
			{"code":"TP","name":"Total Protein","unit":"g/dL",
			 "reference_range":{"dog":"5.4-8.2","cat":"5.4-8.2"}}
		  ],
		  "references": [
			{"title":"VETSCAN VS2 Reference Ranges (Common Units)",
			 "source":"Zoetis Diagnostics",
			 "link":"VTS-00038 (PDF)"}  # citation below
		  ]
		},

		"VetScan HM5": {
		  "info": {
			"type": "자동혈구분석기 (5-part differential Hematology Analyzer)",
			"release": "VetScan HM5",
			"method": "염색 + 광학/임피던스 계수",
			"target": "개, 고양이 포함 다종",
			"features": "약 22~24개 파라미터, 4분 내 결과, 5-part 또는 3-part",
			"integration": "Abaxis Data Manager / 병원 LIS 연동",
			"market": "중소형 동물병원용 CBC 표준기",
			"notes": "종별 모드에 따른 파라미터/레퍼런스가 다를 수 있음.",
            "auto_expand_cbc": False,
		  },
		  "tests": [
			{"code":"WBC","name":"White Blood Cells","unit":"10^9 cells/L",
			 "reference_range":{"dog":"6.0-17.0","cat":"3.5-20.7"}},
			{"code":"LYM","name":"Lymphocytes","unit":"10^9 cells/L",
			 "reference_range":{"dog":"1.0-4.8","cat":"0.83-9.10"}},
			{"code":"MON","name":"Monocytes","unit":"10^9 cells/L",
			 "reference_range":{"dog":"0.20-1.50","cat":"0.09-1.21"}},
			{"code":"NEU(GRA)","name":"Neutrophils (Granulocytes)","unit":"10^9 cells/L",
			 "reference_range":{"dog":"3.0-12.0","cat":"1.63-13.37"}},
			{"code":"EOS","name":"Eosinophils","unit":"10^9 cells/L",
			 "reference_range":{"dog":"0-0.80","cat":"0.02-0.49"}},
			{"code":"RBC","name":"Red Blood Cells","unit":"10^12 cells/L",
			 "reference_range":{"dog":"5.50-8.50","cat":"7.70-12.80"}},
			{"code":"HCT","name":"Hematocrit","unit":"%","reference_range":{"dog":"37.0-55.0","cat":"33.7-55.4"}},
			{"code":"HGB","name":"Hemoglobin","unit":"g/dL","reference_range":{"dog":"12.0-18.0","cat":"10.0-17.0"}},
			{"code":"MCV","name":"Mean Corpuscular Volume","unit":"fL","reference_range":{"dog":"60-77","cat":"35-52"}},
			{"code":"MCH","name":"Mean Corpuscular Hemoglobin","unit":"pg","reference_range":{"dog":"19.5-24.5","cat":"10.0-16.9"}},
			{"code":"MCHC","name":"Mean Corpuscular Hgb Conc.","unit":"g/dL",
			 "reference_range":{"dog":"31.0-39.0","cat":"27.0-35.0"}},
			{"code":"RDWc","name":"Red Cell Distribution Width (CV)","unit":"%","reference_range":{"dog":"14.0-20.0","cat":"18.3-24.1"}},
			{"code":"PLT","name":"Platelets","unit":"10^9 cells/L","reference_range":{"dog":"165-500","cat":"125-618"}},
			{"code":"MPV","name":"Mean Platelet Volume","unit":"fL","reference_range":{"dog":"3.9-11.1","cat":"8.6-14.9"}}
		  ],
		  "references": [
			{"title":"Vetscan HM5 Reference Intervals (Common Species)",
			 "source":"Zoetis Diagnostics",
			 "link":"VTS-00426 (PDF)"}  # citation below
		  ]
		},

		"VetScan VSpro": {
		  "info": {
			"type": "응고 분석기 (Coagulation / Specialty Analyzer)",
			"release": "VetScan VSpro",
			"method": "광학 검출 기반 마이크로채널 카트리지 (PT/aPTT 콤보, Fibrinogen 등)",
			"target": "개·고양이(PT/aPTT), 말(피브리노겐) 등",
			"features": "시트레이트 전혈 1방울로 PT와 aPTT 동시 측정, 약 10분",
			"integration": "VetScan Cloud / 병원 시스템",
			"market": "POC 응고 스크리닝용",
			"notes": "참조범위는 병원/리전·키트에 따라 다르며, 장비 매뉴얼은 범위보다 사용법·검체 요건을 상세 안내"
		  },
		  "tests": [
			{"code":"PT","name":"Prothrombin Time","unit":"seconds",
			 "reference_range":{"dog":"병원 기준 설정","cat":"병원 기준 설정"}},
			{"code":"aPTT","name":"Activated Partial Thromboplastin Time","unit":"seconds",
			 "reference_range":{"dog":"병원 기준 설정","cat":"병원 기준 설정"}},
			{"code":"FIB","name":"Fibrinogen (equine option)","unit":"mg/dL",
			 "reference_range":{"equine":"병원/키트 기준 설정"}}
		  ],
		  "references": [
			{"title":"VetScan VSpro Operator's Manual (PT/aPTT)",
			 "source":"Zoetis Diagnostics",
			 "link":"ABX-00100 (PDF)"},
			{"title":"VSpro PT/aPTT Combination Test — Package Insert",
			 "source":"Zoetis Diagnostics",
			 "link":"LBL-02475 (PDF)"}
		  ]
		},
		
        "i-STAT Alinity V": {
            "info": {
                "type": "혈액가스/전해질 POC 분석기 (Handheld Blood Gas & Chemistry Analyzer)",
                "release": "i-STAT Alinity V (2020~)",
                "method": "전극기반 Microfluidic Cartridge (Na+, K+, Cl-, pH, pCO2, pO2 등)",
                "target": "개, 고양이",
                "features": (
                    "휴대형 반응 카트리지 기반 전혈 분석기. "
                    "각 카트리지에 따라 Chem8+, CG4+, EC8+, G3+ 등 다양한 파라미터 선택 가능."
                ),
                "integration": "Zoetis VETSCAN FUSE / Cloud Reporting",
                "market": "응급/중환자 환경용 POC 혈가스/전해질 분석기"
            },
            "tests": [
                {"code":"pH","name":"pH (Blood)","unit":"",
                 "reference_range":{"dog":"7.35-7.45","cat":"7.30-7.45"}},
                {"code":"Na","name":"Sodium","unit":"mmol/L",
                 "reference_range":{"dog":"138-160","cat":"142-164"}},
                {"code":"K","name":"Potassium","unit":"mmol/L",
                 "reference_range":{"dog":"3.7-5.8","cat":"3.4-4.9"}},
                {"code":"Cl","name":"Chloride","unit":"mmol/L",
                 "reference_range":{"dog":"106-120","cat":"112-126"}},
                {"code":"HCO3","name":"Bicarbonate","unit":"mmol/L",
                 "reference_range":{"dog":"18-26","cat":"18-26"}},
                {"code":"pCO2","name":"Partial Pressure of CO₂","unit":"mmHg",
                 "reference_range":{"dog":"30-40","cat":"32-38"}},
                {"code":"pO2","name":"Partial Pressure of O₂","unit":"mmHg",
                 "reference_range":{"dog":"85-100","cat":"85-100"}},
                {"code":"LAC","name":"Lactate","unit":"mmol/L",
                 "reference_range":{"dog":"0.5-2.5","cat":"0.5-2.5"}},
                {"code":"GLU","name":"Glucose","unit":"mg/dL",
                 "reference_range":{"dog":"60-110","cat":"70-150"}},
                {"code":"BUN","name":"Blood Urea Nitrogen","unit":"mg/dL",
                 "reference_range":{"dog":"7-25","cat":"10-30"}}
            ],
            "references": [
                {"title":"i-STAT Alinity V System Reference Ranges",
                 "source":"Zoetis Diagnostics 2023",
                 "link":"https://www.zoetisus.com/animal-health-products/istat-alinity-v/"}
            ]
        }		
	  },
    "FUJI": {
        "DRI-CHEM NX500": {
            "info": {
                "type": "건식 화학 분석기 (Dry Chemistry Analyzer)",
                "release": "DRI-CHEM NX500 / NX500V / NX500i",
                "method": "건식 슬라이드 광도법 + 선택적 전해질 모듈(ISE)",
                "target": "개, 고양이 등 소형동물",
                "features": (
                    "1검체 처리형. 건식 슬라이드 방식으로 23 화학항목 + 3 전해질(Na, K, Cl) 분석. "
                    "자동 희석, PF(Plasma Filter) 적용 가능, QC 카드 교정 내장."
                ),
                "integration": "병원 LIS 또는 FUJI DMS 연동",
                "market": "소형 동물병원용. 신속 결과(약 6분)와 콤팩트한 크기로 인기.",
                "notes": "측정 범위는 슬라이드 종류별 다름. 일부 항목은 Vet 전용 슬라이드 필요."
            },
            "tests": [
                {"code":"ALB","name":"Albumin","unit":"g/dL",
                 "reference_range":{"dog":"2.5-4.4","cat":"2.2-4.4"}},
                {"code":"ALP","name":"Alkaline Phosphatase","unit":"U/L",
                 "reference_range":{"dog":"20-150","cat":"10-90"}},
                {"code":"ALT","name":"Alanine Aminotransferase","unit":"U/L",
                 "reference_range":{"dog":"10-118","cat":"20-107"}},
                {"code":"AST","name":"Aspartate Aminotransferase","unit":"U/L",
                 "reference_range":{"dog":"14-45","cat":"12-43"}},
                {"code":"BUN","name":"Blood Urea Nitrogen","unit":"mg/dL",
                 "reference_range":{"dog":"7-25","cat":"10-30"}},
                {"code":"CRE","name":"Creatinine","unit":"mg/dL",
                 "reference_range":{"dog":"0.3-1.4","cat":"0.3-2.1"}},
                {"code":"GLU","name":"Glucose","unit":"mg/dL",
                 "reference_range":{"dog":"60-110","cat":"70-150"}},
                {"code":"GGT","name":"Gamma-Glutamyl Transferase","unit":"U/L",
                 "reference_range":{"dog":"0-7","cat":"0-2"}},
                {"code":"TCHO","name":"Total Cholesterol","unit":"mg/dL",
                 "reference_range":{"dog":"125-270","cat":"90-205"}},
                {"code":"TG","name":"Triglyceride","unit":"mg/dL",
                 "reference_range":{"dog":"<150","cat":"<150"}},
                {"code":"TP","name":"Total Protein","unit":"g/dL",
                 "reference_range":{"dog":"5.4-8.2","cat":"5.4-8.2"}},
                {"code":"Ca","name":"Calcium","unit":"mg/dL",
                 "reference_range":{"dog":"8.6-11.8","cat":"8.0-11.8"}},
                {"code":"IP","name":"Inorganic Phosphorus","unit":"mg/dL",
                 "reference_range":{"dog":"2.5-6.8","cat":"3.5-8.5"}},
                {"code":"Mg","name":"Magnesium","unit":"mg/dL",
                 "reference_range":{"dog":"1.6-2.5","cat":"1.6-2.4"}},
                {"code":"LDH","name":"Lactate Dehydrogenase","unit":"U/L",
                 "reference_range":{"dog":"60-350","cat":"70-370"}},
                {"code":"CPK","name":"Creatine Phosphokinase","unit":"U/L",
                 "reference_range":{"dog":"50-400","cat":"60-500"}},
                {"code":"v-AMYL","name":"Amylase (Vet)","unit":"U/L",
                 "reference_range":{"dog":"200-1200","cat":"300-1100"}},
                {"code":"v-LIP","name":"Lipase (Vet)","unit":"U/L",
                 "reference_range":{"dog":"<450","cat":"<450"}},
                {"code":"NH3","name":"Ammonia","unit":"µmol/L",
                 "reference_range":{"dog":"16-80","cat":"23-78"}},
                {"code":"TBIL","name":"Total Bilirubin","unit":"mg/dL",
                 "reference_range":{"dog":"0.1-0.5","cat":"0.5-0.6"}},
                {"code":"TCO2","name":"Total CO2 (Bicarbonate)","unit":"mmol/L",
                 "reference_range":{"dog":"18-26","cat":"18-26"}},
                {"code":"Na","name":"Sodium","unit":"mmol/L",
                 "reference_range":{"dog":"138-160","cat":"142-164"}},
                {"code":"K","name":"Potassium","unit":"mmol/L",
                 "reference_range":{"dog":"3.7-5.8","cat":"3.4-4.9"}},
                {"code":"Cl","name":"Chloride","unit":"mmol/L",
                 "reference_range":{"dog":"106-120","cat":"112-126"}}
            ]
        }
    },
    "IDEXX": {
        "Catalyst One": {
            "info": {
                "type": "혈청화학 분석기 (Clinical Chemistry Analyzer)",
                "release": "Catalyst One (2014년 출시, Catalyst Dx 후속)",
                "method": "건식 슬라이드(Dry Slide) 광도법 + 전해질 모듈 병행",
                "target": "개, 고양이, 소형동물",
                "features": (
                    "CLIP 프로파일(Chem 10/15/17 등) 및 단일 슬라이드 검사 지원. "
                    "1회 시료로 화학·전해질·T4 등 동시 분석. "
                    "자동 보정, VetLab Station 완전 연동."
                ),
                "integration": "VetLab Station / VetConnect PLUS",
                "market": "전 세계 수의 임상에서 표준급 인하우스 분석기"
            },
            "tests": [
                {"code":"ALB","name":"Albumin","unit":"g/dL",
                 "reference_range":{"dog":"2.5-4.4","cat":"2.2-4.4"}},
                {"code":"ALKP","name":"Alkaline Phosphatase","unit":"U/L",
                 "reference_range":{"dog":"20-150","cat":"10-90"}},
                {"code":"ALT","name":"Alanine Aminotransferase","unit":"U/L",
                 "reference_range":{"dog":"10-118","cat":"20-100"}},
                {"code":"AMYL","name":"Amylase","unit":"U/L",
                 "reference_range":{"dog":"200-1200","cat":"300-1100"}},
                {"code":"AST","name":"Aspartate Aminotransferase","unit":"U/L",
                 "reference_range":{"dog":"14-45","cat":"12-43"}},
                {"code":"BUN","name":"Blood Urea Nitrogen","unit":"mg/dL",
                 "reference_range":{"dog":"7-25","cat":"10-30"}},
                {"code":"Ca","name":"Calcium","unit":"mg/dL",
                 "reference_range":{"dog":"8.6-11.8","cat":"8.0-11.8"}},
                {"code":"CHOL","name":"Cholesterol","unit":"mg/dL",
                 "reference_range":{"dog":"125-270","cat":"90-205"}},
                {"code":"CREA","name":"Creatinine","unit":"mg/dL",
                 "reference_range":{"dog":"0.3-1.4","cat":"0.3-2.1"}},
                {"code":"GLU","name":"Glucose","unit":"mg/dL",
                 "reference_range":{"dog":"60-110","cat":"70-150"}},
                {"code":"TP","name":"Total Protein","unit":"g/dL",
                 "reference_range":{"dog":"5.4-8.2","cat":"5.4-8.2"}},
                {"code":"PHOS","name":"Phosphorus","unit":"mg/dL",
                 "reference_range":{"dog":"2.5-6.8","cat":"3.5-8.5"}},
                {"code":"T4","name":"Total Thyroxine","unit":"µg/dL",
                 "reference_range":{"dog":"1.1-4.0","cat":"1.5-4.8"}}
            ],
            "references": [
                {"title":"Catalyst One & Catalyst Dx Reference Ranges",
                 "source":"IDEXX VetLab (VTS-00347-EN, 2023)",
                 "link":"https://www.idexx.com/files/catalyst-species-reference-ranges.pdf"}
            ]
        },

        "ProCyte Dx": {
            "info": {
                "type": "자동혈구분석기 (Hematology Analyzer)",
                "release": "ProCyte Dx (2010년대 중반)",
                "method": "레이저 산란 + 형광 염색 유세포 분석",
                "target": "개, 고양이, 소형동물",
                "features": (
                    "CBC + 5-part WBC differential + 망상적혈구 및 세포 내 지표 포함. "
                    "IDEXX VetLab Station과 실시간 데이터 통합."
                ),
                "integration": "VetLab Station / VetConnect PLUS",
                "market": "수의 임상용 5-part 혈구 분석기 표준",
                "auto_expand_cbc": False,
            },
            "tests": [
                {"code":"WBC","name":"White Blood Cells","unit":"10^3/µL",
                 "reference_range":{"dog":"6.0-17.0","cat":"3.5-20.7"}},
                {"code":"RBC","name":"Red Blood Cells","unit":"10^6/µL",
                 "reference_range":{"dog":"5.5-8.5","cat":"7.7-12.8"}},
                {"code":"HGB","name":"Hemoglobin","unit":"g/dL",
                 "reference_range":{"dog":"12.0-18.0","cat":"10.0-17.0"}},
                {"code":"HCT","name":"Hematocrit","unit":"%",
                 "reference_range":{"dog":"37.0-55.0","cat":"33.7-55.4"}},
                {"code":"MCV","name":"Mean Corpuscular Volume","unit":"fL",
                 "reference_range":{"dog":"60-77","cat":"35-52"}},
                {"code":"MCHC","name":"Mean Corpuscular Hgb Conc.","unit":"g/dL",
                 "reference_range":{"dog":"31-39","cat":"27-35"}},
                {"code":"PLT","name":"Platelets","unit":"10^3/µL",
                 "reference_range":{"dog":"165-500","cat":"125-618"}},
                {"code":"RETIC%","name":"Reticulocyte %","unit":"%",
                 "reference_range":{"dog":"0.5-1.5","cat":"0.2-1.5"}},
                {"code":"RETIC#","name":"Reticulocyte #","unit":"10^3/µL",
                 "reference_range":{"dog":"10-110","cat":"10-100"}}
            ],
            "references": [
                {"title":"ProCyte Dx Reference Intervals (Canine/Feline)",
                 "source":"IDEXX VetLab (VTS-00349-EN, 2023)",
                 "link":"https://www.idexx.com/files/procyte-dx-reference-ranges-en.pdf"}
            ]
        },

        "Catalyst Dx": {
            "info": {
                "type": "혈청화학 분석기 (Clinical Chemistry Analyzer)",
                "release": "Catalyst Dx (2010년대 초반, Catalyst One 전 모델)",
                "method": "건식 슬라이드(Dry Slide) 광도법",
                "target": "개, 고양이, 소형동물",
                "features": "Catalyst One과 동일한 슬라이드 세트를 공유. 처리량이 많고 연결형 디자인.",
                "integration": "VetLab Station",
                "market": "Catalyst One 등장 이전 주력 모델"
            },
            "tests": [
                {"code":"ALB","name":"Albumin","unit":"g/dL",
                 "reference_range":{"dog":"2.5-4.4","cat":"2.2-4.4"}},
                {"code":"ALT","name":"Alanine Aminotransferase","unit":"U/L",
                 "reference_range":{"dog":"10-118","cat":"20-100"}},
                {"code":"BUN","name":"Blood Urea Nitrogen","unit":"mg/dL",
                 "reference_range":{"dog":"7-25","cat":"10-30"}},
                {"code":"CREA","name":"Creatinine","unit":"mg/dL",
                 "reference_range":{"dog":"0.3-1.4","cat":"0.3-2.1"}},
                {"code":"TP","name":"Total Protein","unit":"g/dL",
                 "reference_range":{"dog":"5.4-8.2","cat":"5.4-8.2"}}
            ],
            "references": [
                {"title":"Catalyst Dx Reference Ranges",
                 "source":"IDEXX Diagnostics (Legacy Model)",
                 "link":"https://www.idexx.com/files/catalyst-species-reference-ranges.pdf"}
            ]
        },

        "LaserCyte Dx": {
            "info": {
                "type": "혈구분석기 (Hematology Analyzer)",
                "release": "LaserCyte Dx (2010년대 초반)",
                "method": "레이저 산란 기반 유세포 계수",
                "target": "개, 고양이, 소형동물",
                "features": (
                    "광산란 기술을 이용해 세포 부피, 복잡도, 형광 특성으로 구분. "
                    "CBC와 백혈구 감별, 망상적혈구, NRBC 검출."
                ),
                "integration": "VetLab Station",
                "market": "ProCyte Dx 이전 세대 CBC 분석기",
                "auto_expand_cbc": False,
            },
            "tests": [
                {"code":"WBC","name":"White Blood Cells","unit":"10^3/µL",
                 "reference_range":{"dog":"6.0-17.0","cat":"3.5-20.7"}},
                {"code":"RBC","name":"Red Blood Cells","unit":"10^6/µL",
                 "reference_range":{"dog":"5.5-8.5","cat":"7.7-12.8"}},
                {"code":"HCT","name":"Hematocrit","unit":"%",
                 "reference_range":{"dog":"37.0-55.0","cat":"33.7-55.4"}},
                {"code":"PLT","name":"Platelets","unit":"10^3/µL",
                 "reference_range":{"dog":"165-500","cat":"125-618"}}
            ],
            "references": [
                {"title":"LaserCyte Dx Operator's Manual",
                 "source":"IDEXX Diagnostics (Legacy)",
                 "link":"https://www.idexx.com/files/lasercyte-dx-operators-guide-en.pdf"}
            ]
        },

        "SNAP Pro Analyzer": {
            "info": {
                "type": "면역반응 기반 신속 진단기 (Immunoassay Analyzer)",
                "release": "SNAP Pro (2018~)",
                "method": "Colorimetric Enzyme Immunoassay (EIA) - SNAP Test Reader",
                "target": "개, 고양이",
                "features": (
                    "IDEXX SNAP 테스트(FeLV/FIV, FIV Ab, Feline ProBNP, CPL, T4 등) 자동 판독. "
                    "기기 자동 인식, VetLab Station 자동 업로드."
                ),
                "integration": "VetLab Station / VetConnect PLUS",
                "market": "POC 신속면역검사 플랫폼"
            },
            "tests": [
                {"code":"SNAP FIV/FeLV","name":"Feline Immunodeficiency & Leukemia Virus","unit":"Positive/Negative",
                 "reference_range":{"dog":"Not established","cat":"Negative"}},
                {"code":"SNAP fPL","name":"Feline Pancreatic Lipase Immunoreactivity","unit":"µg/L",
                 "reference_range":{"dog":"Not established","cat":"< 3.5 (정상)"}},
                {"code":"SNAP T4","name":"Total T4 (Immunoassay)","unit":"µg/dL",
                 "reference_range":{"dog":"1.1-4.0","cat":"1.5-4.8"}},
                {"code":"SNAP BNP","name":"Feline NT-proBNP","unit":"pmol/L",
                 "reference_range":{"dog":"Not established","cat":"< 100 (정상)"}}
            ],
            "references": [
                {"title":"SNAP Pro Analyzer Operator's Manual",
                 "source":"IDEXX Diagnostics",
                 "link":"https://www.idexx.com/en/veterinary/analyzers/snap-pro-analyzer/"}
            ]
        },
		
        "VetStat": {
            "info": {
                "type": "혈액가스/전해질 분석기 (Blood Gas & Electrolyte Analyzer)",
                "release": "VetStat (2010년대 초반)",
                "method": "이온선택전극(ISE) + 전극형 혈액가스 분석",
                "target": "개, 고양이, 말, 반려동물",
                "features": (
                    "소량의 전혈로 전해질 및 혈액가스(pH, pCO₂, pO₂, HCO₃⁻ 등) 분석. "
                    "전용 카트리지 기반, Catalyst/ProCyte와 동일 VetLab Station 연동."
                ),
                "integration": "VetLab Station / VetConnect PLUS",
                "market": "소형~대형병원용 혈액가스 전해질 분석기"
            },
            "tests": [
                {"code":"pH","name":"pH (Blood)","unit":"",
                 "reference_range":{"dog":"7.35-7.45","cat":"7.30-7.45"}},
                {"code":"Na","name":"Sodium","unit":"mmol/L",
                 "reference_range":{"dog":"138-160","cat":"142-164"}},
                {"code":"K","name":"Potassium","unit":"mmol/L",
                 "reference_range":{"dog":"3.7-5.8","cat":"3.4-4.9"}},
                {"code":"Cl","name":"Chloride","unit":"mmol/L",
                 "reference_range":{"dog":"106-120","cat":"112-126"}},
                {"code":"HCO3","name":"Bicarbonate","unit":"mmol/L",
                 "reference_range":{"dog":"18-26","cat":"18-26"}},
                {"code":"pCO2","name":"Partial Pressure of CO₂","unit":"mmHg",
                 "reference_range":{"dog":"30-40","cat":"32-38"}},
                {"code":"pO2","name":"Partial Pressure of O₂","unit":"mmHg",
                 "reference_range":{"dog":"85-100","cat":"85-100"}}
            ],
            "references": [
                {"title":"VetStat Electrolyte and Blood Gas Analyzer Operator's Manual",
                 "source":"IDEXX Laboratories (VTS-00412-EN)",
                 "link":"https://www.idexx.com/en/veterinary/analyzers/vetstat-electrolyte-and-blood-gas-analyzer/"}
            ]
        },

        "Coag Dx": {
            "info": {
                "type": "혈액응고 분석기 (Coagulation Analyzer)",
                "release": "Coag Dx (2012~)",
                "method": "전기 임피던스 기반 프로트롬빈 시간(PT) 및 활성화 부분 트롬보플라스틴 시간(aPTT) 측정",
                "target": "개, 고양이",
                "features": (
                    "소량 전혈로 PT/aPTT 자동 측정. 결과를 VetLab Station에 자동 전송. "
                    "카트리지 방식, 교정 불필요. Coag Dx 전용 PT/aPTT 시약 사용."
                ),
                "integration": "VetLab Station / VetConnect PLUS",
                "market": "소형동물용 Point-of-Care 응고 분석기"
            },
            "tests": [
                {"code":"PT","name":"Prothrombin Time","unit":"seconds",
                 "reference_range":{"dog":"7-10","cat":"10-15"}},
                {"code":"aPTT","name":"Activated Partial Thromboplastin Time","unit":"seconds",
                 "reference_range":{"dog":"9-12","cat":"13-20"}}
            ],
            "references": [
                {"title":"Coag Dx Analyzer Reference Intervals (Canine/Feline)",
                 "source":"IDEXX Diagnostics (Technical Bulletin, 2022)",
                 "link":"https://www.idexx.com/en/veterinary/analyzers/coag-dx-analyzer/"}
            ]
        },

        "VetLab UA": {
            "info": {
                "type": "요화학 분석기 (Urinalysis Analyzer)",
                "release": "VetLab UA (2010년대)",
                "method": "포토메트릭 반사광 스트립 판독",
                "target": "개, 고양이",
                "features": (
                    "소변 스트립의 반사광을 측정하여 Glucose, Protein, pH, SG, Ketone 등 자동 판독. "
                    "ProCyte/Catalyst 결과와 통합되어 임상 해석 지원."
                ),
                "integration": "VetLab Station / VetConnect PLUS",
                "market": "소형동물용 자동 요화학 분석기"
            },
            "tests": [
                {"code":"GLU","name":"Urine Glucose","unit":"mg/dL",
                 "reference_range":{"dog":"Negative","cat":"Negative"}},
                {"code":"PRO","name":"Urine Protein","unit":"mg/dL",
                 "reference_range":{"dog":"Negative-Trace","cat":"Negative-Trace"}},
                {"code":"pH","name":"Urine pH","unit":"",
                 "reference_range":{"dog":"5.5-7.0","cat":"6.0-7.5"}},
                {"code":"SG","name":"Specific Gravity","unit":"",
                 "reference_range":{"dog":"1.015-1.045","cat":"1.020-1.060"}},
                {"code":"KET","name":"Ketones","unit":"mg/dL",
                 "reference_range":{"dog":"Negative","cat":"Negative"}},
                {"code":"BIL","name":"Bilirubin","unit":"mg/dL",
                 "reference_range":{"dog":"Negative","cat":"Negative"}},
                {"code":"BLO","name":"Blood (Hemoglobin)","unit":"cells/µL",
                 "reference_range":{"dog":"Negative","cat":"Negative"}}
            ],
            "references": [
                {"title":"VetLab UA Analyzer Operator's Manual",
                 "source":"IDEXX Laboratories",
                 "link":"https://www.idexx.com/en/veterinary/analyzers/vetlab-ua-analyzer/"}
            ]
        },

        "SediVue Dx": {
            "info": {
                "type": "자동 요침사 현미경 분석기 (Automated Urine Sediment Analyzer)",
                "release": "SediVue Dx (2017~)",
                "method": "디지털 현미경 + 이미지 분석 AI",
                "target": "개, 고양이",
                "features": (
                    "요침사 자동 판독. RBC, WBC, Bacteria, Crystals 등 AI 기반 세포 이미지 분석. "
                    "약 3분 내 결과, 이미지 리뷰 및 수동 확인 기능 포함."
                ),
                "integration": "VetLab Station / VetConnect PLUS",
                "market": "소형동물용 자동 현미경 분석기 (요침사 판독)"
            },
            "tests": [
                {"code":"RBC","name":"Red Blood Cells (Urine)","unit":"/hpf",
                 "reference_range":{"dog":"0-3","cat":"0-3"}},
                {"code":"WBC","name":"White Blood Cells (Urine)","unit":"/hpf",
                 "reference_range":{"dog":"0-5","cat":"0-5"}},
                {"code":"Bacteria","name":"Bacteria","unit":"qualitative",
                 "reference_range":{"dog":"None seen","cat":"None seen"}},
                {"code":"Crystals","name":"Crystals (Struvite, CaOx, etc.)","unit":"qualitative",
                 "reference_range":{"dog":"None seen","cat":"None seen"}}
            ],
            "references": [
                {"title":"SediVue Dx Operator's Guide",
                 "source":"IDEXX Diagnostics (AI Imaging System)",
                 "link":"https://www.idexx.com/en/veterinary/analyzers/sedivue-dx-urine-sediment-analyzer/"}
            ]
        }		
    },

    "Mindray": {
        "BS-240 Vet": {
            "info": {
                "type": "혈청화학 분석기 (Clinical Chemistry Analyzer)",
                "release": "BS-240 Vet (2018 ~)",
                "method": "광도법 + ISE 모듈",
                "target": "개, 고양이 등 소형동물",
                "features": (
                    "처리속도 200 tests/hour, 23 화학 + 전해질(Na, K, Cl) 지원. "
                    "자동 희석 및 세척 기능 내장, vet-전용 프로그램 탑재."
                ),
                "integration": "LIS 연동 가능",
                "market": "중소형 병원용 자동 화학 분석기"
            },
            "tests": [
                {"code":"ALB","name":"Albumin","unit":"g/dL",
                 "reference_range":{"dog":"2.5-4.4","cat":"2.2-4.4"}},
                {"code":"ALKP","name":"Alkaline Phosphatase","unit":"U/L",
                 "reference_range":{"dog":"20-150","cat":"10-90"}},
                {"code":"ALT","name":"Alanine Aminotransferase","unit":"U/L",
                 "reference_range":{"dog":"10-118","cat":"20-107"}},
                {"code":"AST","name":"Aspartate Aminotransferase","unit":"U/L",
                 "reference_range":{"dog":"14-45","cat":"12-43"}},
                {"code":"BUN","name":"Blood Urea Nitrogen","unit":"mg/dL",
                 "reference_range":{"dog":"7-25","cat":"10-30"}},
                {"code":"CREA","name":"Creatinine","unit":"mg/dL",
                 "reference_range":{"dog":"0.3-1.4","cat":"0.3-2.1"}},
                {"code":"GLU","name":"Glucose","unit":"mg/dL",
                 "reference_range":{"dog":"60-110","cat":"70-150"}},
                {"code":"CHOL","name":"Cholesterol","unit":"mg/dL",
                 "reference_range":{"dog":"125-270","cat":"90-205"}},
                {"code":"TP","name":"Total Protein","unit":"g/dL",
                 "reference_range":{"dog":"5.4-8.2","cat":"5.4-8.2"}},
                {"code":"GGT","name":"Gamma-Glutamyl Transferase","unit":"U/L",
                 "reference_range":{"dog":"0-7","cat":"0-2"}},
                {"code":"Ca","name":"Calcium","unit":"mg/dL",
                 "reference_range":{"dog":"8.6-11.8","cat":"8.0-11.8"}},
                {"code":"PHOS","name":"Phosphorus","unit":"mg/dL",
                 "reference_range":{"dog":"2.5-6.8","cat":"3.5-8.5"}},
                {"code":"Na","name":"Sodium","unit":"mmol/L",
                 "reference_range":{"dog":"138-160","cat":"142-164"}},
                {"code":"K","name":"Potassium","unit":"mmol/L",
                 "reference_range":{"dog":"3.7-5.8","cat":"3.4-4.9"}},
                {"code":"Cl","name":"Chloride","unit":"mmol/L",
                 "reference_range":{"dog":"106-120","cat":"112-126"}},
                {"code":"T4","name":"Total Thyroxine","unit":"µg/dL",
                 "reference_range":{"dog":"1.1-4.0","cat":"1.5-4.8"}}
            ],
            "references": [
                {"title":"BS-240 Vet Reference Intervals (Canine/Feline)",
                 "source":"Mindray Vet Division & VetLab Companion Ref. 2023",
                 "link":"https://www.mindray.com/en/products/laboratory-diagnostics/chemistry/bs-240-vet"}
            ]
        },

        "BC-2800 Vet": {
            "info": {
                "type": "자동 혈구분석기 (Hematology Analyzer)",
                "release": "BC-2800 Vet (2016 ~)",
                "method": "전기 임피던스 + 비시안 Hb 색도법",
                "target": "개, 고양이 등",
                "features": (
                    "19 parameters + 3 histograms, 3-part WBC 감별. "
                    "소형 병원 용도에 적합하며 개/고양이 프로파일 내장."
                ),
                "integration": "LIS 연동 가능",
                "market": "중소형 동물병원용 CBC 장비",
                "auto_expand_cbc": False,
            },
            "tests": [
                {"code":"WBC","name":"White Blood Cells","unit":"10^3/µL",
                 "reference_range":{"dog":"6.0-17.0","cat":"3.5-20.7"}},
                {"code":"RBC","name":"Red Blood Cells","unit":"10^6/µL",
                 "reference_range":{"dog":"5.5-8.5","cat":"7.7-12.8"}},
                {"code":"HGB","name":"Hemoglobin","unit":"g/dL",
                 "reference_range":{"dog":"12.0-18.0","cat":"10.0-17.0"}},
                {"code":"HCT","name":"Hematocrit","unit":"%",
                 "reference_range":{"dog":"37.0-55.0","cat":"33.7-55.4"}},
                {"code":"MCV","name":"Mean Corpuscular Volume","unit":"fL",
                 "reference_range":{"dog":"60-77","cat":"35-52"}},
                {"code":"MCHC","name":"Mean Corpuscular Hgb Conc.","unit":"g/dL",
                 "reference_range":{"dog":"31-39","cat":"27-35"}},
                {"code":"PLT","name":"Platelets","unit":"10^3/µL",
                 "reference_range":{"dog":"165-500","cat":"125-618"}},
                {"code":"RDW","name":"Red Cell Distribution Width","unit":"%",
                 "reference_range":{"dog":"11-15","cat":"11-16"}},
                {"code":"LYM%","name":"Lymphocytes %","unit":"%",
                 "reference_range":{"dog":"12-30","cat":"20-55"}},
                {"code":"MONO%","name":"Monocytes %","unit":"%",
                 "reference_range":{"dog":"3-10","cat":"1-4"}},
                {"code":"GRAN%","name":"Granulocytes %","unit":"%",
                 "reference_range":{"dog":"60-80","cat":"35-75"}},
                {"code":"EOS%","name":"Eosinophils %","unit":"%",
                 "reference_range":{"dog":"2-10","cat":"2-10"}},
                {"code":"RETIC%","name":"Reticulocytes %","unit":"%",
                 "reference_range":{"dog":"0.5-1.5","cat":"0.2-1.5"}}
            ],
            "references": [
                {"title":"BC-2800 Vet Reference Intervals (Canine/Feline)",
                 "source":"Mindray Vet Division Technical Reference 2023",
                 "link":"https://www.mindray.com/en/products/laboratory-diagnostics/hematology/bc-2800-vet"}
            ]
        }
    },
	
    "Diatron": {
        "LABGEO PT10V": {
            "info": {
                "type": "건식 혈청화학 분석기 (Dry Clinical Chemistry Analyzer)",
                "release": "LABGEO PT10V (2013~, Diatron 협업 모델)",
                "method": "건식 로터(디스크) 기반 광도법 (Dry Rotor Photometric)",
                "target": "개, 고양이 등 소형동물",
                "features": (
                    "1회 로터(디스크) 기반 다항목 자동 측정 (최대 15항목). "
                    "소량의 전혈/혈청/혈장(70 µL)으로 7분 이내 결과 제공. "
                    "내장 캘리브레이션 및 자동 QC. Wi-Fi / LIS 연동 지원."
                ),
                "integration": "LIS 연동, USB 또는 Wi-Fi 데이터 전송",
                "market": "국내 소동물병원 및 검진센터용 소형 화학 분석기",
                "notes": "IDEXX Catalyst One 및 Abaxis VS2와 유사한 건식 로터 구조."
            },
            "tests": [
                {"code":"ALB","name":"Albumin","unit":"g/dL",
                 "reference_range":{"dog":"2.5-4.4","cat":"2.2-4.4"}},
                {"code":"ALP","name":"Alkaline Phosphatase","unit":"U/L",
                 "reference_range":{"dog":"20-150","cat":"10-90"}},
                {"code":"ALT","name":"Alanine Aminotransferase","unit":"U/L",
                 "reference_range":{"dog":"10-118","cat":"20-107"}},
                {"code":"AST","name":"Aspartate Aminotransferase","unit":"U/L",
                 "reference_range":{"dog":"14-45","cat":"12-43"}},
                {"code":"BUN","name":"Blood Urea Nitrogen","unit":"mg/dL",
                 "reference_range":{"dog":"7-25","cat":"10-30"}},
                {"code":"CRE","name":"Creatinine","unit":"mg/dL",
                 "reference_range":{"dog":"0.3-1.4","cat":"0.3-2.1"}},
                {"code":"GLU","name":"Glucose","unit":"mg/dL",
                 "reference_range":{"dog":"60-110","cat":"70-150"}},
                {"code":"CHOL","name":"Cholesterol","unit":"mg/dL",
                 "reference_range":{"dog":"125-270","cat":"90-205"}},
                {"code":"TP","name":"Total Protein","unit":"g/dL",
                 "reference_range":{"dog":"5.4-8.2","cat":"5.4-8.2"}},
                {"code":"Ca","name":"Calcium","unit":"mg/dL",
                 "reference_range":{"dog":"8.6-11.8","cat":"8.0-11.8"}},
                {"code":"PHOS","name":"Phosphorus","unit":"mg/dL",
                 "reference_range":{"dog":"2.5-6.8","cat":"3.5-8.5"}},
                {"code":"TBIL","name":"Total Bilirubin","unit":"mg/dL",
                 "reference_range":{"dog":"0.1-0.5","cat":"0.5-0.6"}},
                {"code":"GGT","name":"Gamma-Glutamyl Transferase","unit":"U/L",
                 "reference_range":{"dog":"0-7","cat":"0-2"}},
                {"code":"Na","name":"Sodium","unit":"mmol/L",
                 "reference_range":{"dog":"138-160","cat":"142-164"}},
                {"code":"K","name":"Potassium","unit":"mmol/L",
                 "reference_range":{"dog":"3.7-5.8","cat":"3.4-4.9"}},
                {"code":"Cl","name":"Chloride","unit":"mmol/L",
                 "reference_range":{"dog":"106-120","cat":"112-126"}}
            ],
            "references": [
                {"title":"LABGEO PT10V Veterinary Chemistry Analyzer Reference Values",
                 "source":"Samsung Medison / Diatron Technical Data Sheet (2018)",
                 "link":"https://www.diatron.com/products/labgeo-pt10v"}
            ]
        },

        "LABGEO HC10": {
            "info": {
                "type": "혈구분석기 (Hematology Analyzer)",
                "release": "LABGEO HC10 (2014~, Diatron 협업)",
                "method": "전기 임피던스 + 흡광 측정 방식 (3-part differential)",
                "target": "개, 고양이 등 소형동물",
                "features": (
                    "CBC 18항목, WBC 3-part differential (NEU, LYM, MONO). "
                    "소형 동물용 설정 내장, 자동 희석 및 폐기 관리."
                ),
                "integration": "LIS 연동 및 자동 결과 저장",
                "market": "소형~중형 동물병원 CBC 분석기",
                "notes": "Mindray BC-2800Vet과 유사한 성능, 국내 기술지원 가능.",
                "auto_expand_cbc": False,
            },
            "tests": [
                {"code":"WBC","name":"White Blood Cells","unit":"10^3/µL",
                 "reference_range":{"dog":"6.0-17.0","cat":"3.5-20.7"}},
                {"code":"RBC","name":"Red Blood Cells","unit":"10^6/µL",
                 "reference_range":{"dog":"5.5-8.5","cat":"7.7-12.8"}},
                {"code":"HGB","name":"Hemoglobin","unit":"g/dL",
                 "reference_range":{"dog":"12.0-18.0","cat":"10.0-17.0"}},
                {"code":"HCT","name":"Hematocrit","unit":"%",
                 "reference_range":{"dog":"37.0-55.0","cat":"33.7-55.4"}},
                {"code":"MCV","name":"Mean Corpuscular Volume","unit":"fL",
                 "reference_range":{"dog":"60-77","cat":"35-52"}},
                {"code":"MCHC","name":"Mean Corpuscular Hgb Conc.","unit":"g/dL",
                 "reference_range":{"dog":"31-39","cat":"27-35"}},
                {"code":"PLT","name":"Platelets","unit":"10^3/µL",
                 "reference_range":{"dog":"165-500","cat":"125-618"}},
                {"code":"NEU%","name":"Neutrophils %","unit":"%",
                 "reference_range":{"dog":"60-80","cat":"35-75"}},
                {"code":"LYM%","name":"Lymphocytes %","unit":"%",
                 "reference_range":{"dog":"12-30","cat":"20-55"}},
                {"code":"MONO%","name":"Monocytes %","unit":"%",
                 "reference_range":{"dog":"3-10","cat":"1-4"}}
            ],
            "references": [
                {"title":"LABGEO HC10 Veterinary Hematology Analyzer Reference Values",
                 "source":"Samsung Medison / Diatron (2018)",
                 "link":"https://www.diatron.com/products/labgeo-hc10"}
            ]
        }
    }	
}

