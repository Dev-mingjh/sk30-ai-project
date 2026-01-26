# 라벨/카테고리/키워드 등 공통 상수 정의

# 모델명 / 파라미터
DEFAULT_EMBED_MODEL = "text-embedding-3-small"
DEFAULT_LLM_MODEL = "gpt-5.2"
DEFAULT_TOP_K = 5

# VectorDB / Collection 이름
COLLECTION_MITRE = "mitre_chunks"
COLLECTION_KISA_REPORT = "kisa_chunks"
COLLECTION_KISA_GUIDE = "kisa_guide_chunks"

# Chunk 파라미터 (MITRE/KISA 공통)
CHUNK_SIZE = 800
CHUNK_OVERLAP = 120

# 경로 기본값
DEFAULT_OUT_DIR = "created_DB"
DEFAULT_CHROMA_SUBDIR = "chroma_db"

# 공격 유형 분류
ATTACK_LABELS = [
    "DDoS",
    "PortScan",
    "Web Attack", 
    "Brute Force",               
    "BotNet",     
    "BENIGN",
    "Infiltration",
    "DoS"         
]

# 라벨 -> ATT&CK Technique 매핑
LABEL_TO_ATTACK = {
    "DDoS": {
        "behavior": "대량의 트래픽을 발생시켜 네트워크 또는 서비스의 가용성을 저하시키는 공격 행위",
        "anchor_techniques": [
            "T1498",
            "T1498.001",
            "T1498.002",
            "T1499.001",
            "T1499.002",
            "T1499.003",
            "T1499.004",
        ],
        "tactics": ["Impact"],
        "notes": [
            "단시간 내 비정상적으로 급증하는 트래픽 패턴이 관찰됨",
            "다수의 출발지 IP 또는 반사(reflection) 기반 트래픽이 특징적으로 나타남",
            "네트워크 대역폭 포화 또는 서비스 응답 지연/중단 현상이 동반됨",
            "사전 단계로 봇넷 감염 또는 증폭 서버 스캔이 선행될 수 있음",
        ],
    },

    "DoS": {
        "behavior": "HTTP 연결을 장시간 유지하여 서버 자원을 고갈시키는 애플리케이션 계층 DoS 공격",
        "anchor_techniques": [
            "T1498",
            "T1498.001",
            "T1498.002",
            "T1499.001",
            "T1499.002",
            "T1499.003",
            "T1499.004",
        ],
        "tactics": ["Impact"],
        "notes": [
            "정상적인 HTTP 요청처럼 보이나 연결을 비정상적으로 오래 유지함",
            "동시 세션 수 증가 대비 트래픽 양은 상대적으로 적은 특징을 보임",
            "웹 서버의 스레드/커넥션 자원 고갈로 서비스 응답 지연이 발생함",
            "KISA 웹 서비스 거부 공격 대응 가이드와 직접적으로 연계 가능",
        ],
    },

    "PortScan": {
        "behavior": "대상 시스템의 열려 있는 포트 및 서비스 정보를 탐색하기 위한 스캔 행위",
        "anchor_techniques": ["T1046"],
        "tactics": ["Discovery"],
        "notes": [
            "다수의 포트에 대해 순차적 또는 병렬적인 연결 시도가 관찰됨",
            "짧은 시간 내 동일 IP 또는 분산 IP에서 반복적인 접속 시도가 발생함",
            "사전 정찰 단계로 이후 취약점 공격 또는 침투 시도의 전조로 활용됨",
            "IDS/방화벽 로그 기반 탐지 및 차단 정책 수립에 활용 가능",
        ],
    },

    "Web Attack": {
        "behavior": "웹 로그인 인터페이스를 대상으로 계정 정보를 반복적으로 추측하는 공격 행위",
        "anchor_techniques": [
            "T1110",
            "T1110.001",
            "T1110.002",
            "T1110.003",
            "T1110.004",
        ],
        "tactics": ["Credential Access"],
        "notes": [
            "웹 로그인 실패 이벤트가 짧은 시간 내 비정상적으로 증가함",
            "특정 계정 또는 다수 계정을 대상으로 한 자동화된 인증 시도가 확인됨",
            "계정 잠금 정책 미적용 시 계정 탈취로 이어질 가능성이 높음",
            "WAF 및 인증 로그 분석을 통한 탐지 및 차단이 핵심 대응 포인트",
        ],
    },

    "Brute Force": {
        "behavior": "웹 로그인 인터페이스를 대상으로 계정 정보를 반복적으로 추측하는 공격 행위",
        "anchor_techniques": [
            "T1110.001",
            "T1110.002",
            "T1110.003",
            "T1110.004",
            "T1595.003",
        ],
        "tactics": ["Credential Access"],
        "notes": [
            "동일 또는 다수 IP에서 반복적인 로그인 실패 패턴이 확인됨",
            "admin, root 등 추측 가능한 계정을 중심으로 공격이 수행됨",
            "요청 간 간격이 일정하거나 자동화 도구 사용 흔적이 존재함",
            "사전 단계로 로그인 페이지 식별 및 서비스 스캔이 선행될 수 있음",
        ],
    },

    "BotNet": {
        "behavior": "감염된 호스트가 외부 명령제어 서버와 통신하는 봇넷 기반 행위",
        "anchor_techniques": [
            "T1071",
            "T1071.001",
            "T1071.004",
        ],
        "tactics": ["Command and Control"],
        "notes": [
            "주기적 또는 비정상적인 외부 서버와의 통신 패턴이 관찰됨",
            "HTTP/HTTPS, DNS 등 애플리케이션 계층 프로토콜을 이용한 C2 통신이 특징",
            "네트워크 트래픽 분석을 통해 지속적 연결 또는 비정상 도메인 접속 탐지 가능",
            "추가 페이로드 다운로드 및 2차 공격의 거점으로 활용될 위험이 있음",
        ],
    },

    "Infiltration": {
        "behavior": "외부 공격자가 내부 네트워크로 침투하여 정보 접근 또는 외부 유출을 시도하는 행위",
        "anchor_techniques": [
            "T1190",
            "T1078",
            "T1204",
            "T1567",
            "T1567.002",
        ],
        "tactics": [
            "Initial Access",
            "Credential Access",
            "Execution",
            "Exfiltration",
        ],
        "notes": [
            "취약한 서비스 또는 유효한 계정을 이용한 내부 접근 시도가 관찰됨",
            "내부 시스템 간 이동(lateral movement) 및 권한 남용 행위가 동반될 수 있음",
            "민감 정보 수집 후 외부 서버로의 유출 징후가 나타날 가능성이 있음",
            "CICIDS Infiltration 시나리오는 침투·수집·유출 단계가 혼재되어 나타남",
        ],
    },

    "BENIGN": {
        "behavior": "정상적인 네트워크 트래픽 및 서비스 이용 행위",
        "anchor_techniques": [],
        "tactics": [],
        "notes": [
            "DB 수집 및 대응 가이드 생성 대상에서 제외",
            "공격 탐지 모델의 베이스라인 설명용 메타 정보로만 활용",
        ],
    },
}

LABEL_NORMALIZE_ALIASES = {
    "DDOS" : "DDos",
    "ddos" : "DDos",

    "DoS": "DoS",
    "dos": "DoS",

    "Port Scan": "PortScan",
    "protscan": "PortScan",
    
    "WebAttack": "Web Attack",
    "Web Attack": "Web Attack",
    
    "Brute Force" : "Brute Force",
    "bruteforce" : "Brute Force",
    
    "Bot": "BotNET",
    "bot": "BotNET",
    "botnet": "BotNET",

    "infiltration": "Infiltration",
}

LABEL_TO_KISA_CATEGORY = {
    "Web Attack": "계정탈취/인증공격",
    "Brute Force" : "계정탈취/인증공격",
    "PortScan": "스캔/정찰",
    "DDoS": "서비스거부(DoS/DDoS)",
    "DoS": "서비스거부(DoS/DDoS)",
    "Infiltration": "침투/내부확산",
    "BotNet": "악성코드/봇넷",
    "BENIGN": "일반/정상",
}

KISA_CATEGORY_KEYWORDS_KO = {
    "계정탈취/인증공격": ["계정탈취", "비밀번호 추측", "무차별 대입", "인증", "로그인 실패", "크리덴셜"],
    "스캔/정찰": ["포트스캔", "스캔", "정찰", "서비스 탐색", "nmap", "배너그래빙"],
    "서비스거부(DoS/DDoS)": ["서비스거부", "디도스", "가용성", "트래픽 폭주", "세션 고갈", "slowloris"],
    "침투/내부확산": ["침투", "권한상승", "내부 확산", "측면이동", "원격접속", "백도어"],
    "악성코드/봇넷": ["봇넷", "C2", "악성코드", "감염", "원격제어", "좀비PC"],
    "일반/정상": ["정상"],
}

LABEL_KEYWORDS = {
    "DDoS": ["디도스", "ddos", "대량", "트래픽 폭주", "가용성"],
    "DoS": ["slowloris", "슬로우리", "느린 요청", "연결 유지", "세션 고갈"],
    "PortScan": ["포트", "스캔", "정찰", "탐색", "nmap"],
    "Web Attack - Brute Force": ["무차별", "대입", "brute", "로그인 실패", "비밀번호", "인증"],
    "BotNet": ["봇넷", "c2", "명령제어", "악성코드", "감염"],
    "Infiltration": ["침투", "내부", "유출", "원격", "확산"],
    "BENIGN": ["정상"],
}

BASE_MITRE_URL = "https://attack.mitre.org"


# web_search 신뢰 도메인 목록 
TRUSTED_SOURCES = [
    # 해외 사이버보안 뉴스
    "https://www.darkreading.com/",
    # 국내 사이버보안 뉴스
    "https://www.boannews.com/",
]

ATTACK_FAMILY_MAP = {
    "DDoS": "DDOS공격",
    "DoS": "DDOS공격",
    "Web Attack": "웹취약점 및 침투 공격",
    "Brute Force": "웹취약점 및 침투 공격",
    "Infiltration": "웹취약점 및 침투 공격",
    "PortScan": "서버 취약점 공격",
    "BotNet": "서버 취약점 공격",
}