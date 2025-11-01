
# 최근 대화(turn) 윈도우 크기 (대화 기록 관리에 사용)
RECENT_TURN_WINDOW = 10

# 대화가 이 값(턴 수)을 넘으면 요약(summarization) 트리거
SUMMARIZE_TRIGGER_TURNS = 10

# RAG(Retrieval-Augmented Generation) 기능 활성화 시 검색 결과 Top-K 기본값
# - 반환되는 검색 결과의 개수
# - 일반적으로 3~20 사이가 적정 (1~50까지도 조정 가능)
# - 값이 작으면 검색 결과가 부족해 정확도가 떨어질 수 있고, 너무 크면 불필요한 정보가 많아지고 성능 저하 가능
# - 현재 프로젝트 기본값: 8
RETRIEVAL_TOP_K = 8
