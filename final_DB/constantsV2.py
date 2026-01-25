# 모델명 / 파라미터
DEFAULT_EMBED_MODEL = "text-embedding-3-small"
DEFAULT_LLM_MODEL = "gpt-5.2"
DEFAULT_TOP_K = 5

# VectorDB / Collection 이름
## 1024 컬렉션 명 통일 _chucks삭제
## 0125 수정: kisa데이터 추가할 예정, 이름 혼동 방지를 위해 kisa-> kisa_report_process로 변경
COLLECTION_MITRE = "mitre" 
COLLECTION_KISA_REPORT = "kisa_report_process"
COLLECTION_KISA_GUIDE = "kisa_guide" ## 새로운 DB내용 추가

# Chunk 파라미터 (MITRE/KISA 공통)
CHUNK_SIZE = 800
CHUNK_OVERLAP = 120

# 경로 기본값
## 1024 DIR: /content는 코랩 기준임, 프로젝트 루트에 저장으로 변경
DEFAULT_OUT_DIR = ""
DEFAULT_CHROMA_SUBDIR = "chroma_db"

# 라벨 목록 / 라벨 정규화
## 1024 모델분리 팀 라벨 변경에 따른 db변경
ATTACK_LABELS = [
    "DDoS",
    "PortScan",
    "Web Attack", ## 1024 수정: web attack, brute forec 분리
    "Brute Force",
                  ## FTP삭제
    "BotNet",     ## 1024 수정: Bot -> BotNet으로 수정
    "BENIGN",
    "Infiltration",
    "DoS"         ## 1024 수정: Dos slowloris -> dos로 수중
]
## 0125: 가이드 검색을 위해 큰 범주로 맵핑_이기찬
ATTACK_FAMILY_MAP = {
    "DDoS": "DDOS공격",
    "DoS": "DDOS공격",
    "Web Attack": "웹취약점 및 침투 공격",
    "Brute Force": "웹취약점 및 침투 공격",
    "Infiltration": "웹취약점 및 침투 공격",
    "PortScan": "서버 취약점 공격",
    "BotNet": "서버 취약점 공격",
}
## 0125 수정: 공격팀 응답 받아오는 거 보고 삭제or 수정필요_이기찬
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

    
    ## 1024 수정: fTP삭제
}

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
        "notes": ["대용량 플러딩, 반사(reflection) 기반 DDoS 포함"],
    },

    ## 1024 수정: slowloris 문구 삭제
    "DoS ": {
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
            "L7 slow DoS, 이후 KISA 문서에서 웹서버/서비스거부 대응 섹션과 강하게 결합"
        ],
    },

    "PortScan": {
        "behavior": "대상 시스템의 열려 있는 포트 및 서비스 정보를 탐색하기 위한 스캔 행위",
        "anchor_techniques": ["T1046"],
        "tactics": ["Discovery"],
        "notes": ["사전 정찰 단계, IDS/방화벽 로그 분석과 연계"],
    },

    ## 1024 Brute Force 제거
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
        "notes": ["로그인 실패 횟수 급증, 계정 잠금 정책 대응"],
    },
    ## 1024 Brute Force 추가
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
        "notes": ["로그인 실패 반복, 다수 계정/단일 계정 대상 시도, 짧은 간격의 인증 요청이 핵심 징후이며 계정 잠금,rate limit,MFA 우회 시도와 함께 나타날 수 있음"],
    },

    "BotNet": {
        "behavior": "감염된 호스트가 외부 명령제어 서버와 통신하는 봇넷 기반 행위",
        "anchor_techniques": ["T1110.002"],
        "tactics": ["Command and Control"],
        "notes": [
            "HTTP/HTTPS 기반 C2면 T1071.001, DNS면 T1071.004로 확장 가능"
        ],
    },
    ## 1024 수정 : FTP삭제
    "Infiltration": {
        "behavior": "외부 공격자가 내부 네트워크로 침투하여 정보 접근 또는 외부 유출을 시도하는 행위",
        "anchor_techniques": [
            "T1567",
            "T1567.002",
            "T1078",
            "T1190",
            "T1204",
        ],
        "tactics": ["Exfiltration"],
        "notes": [
            "CICIDS Infiltration은 lateral movement/collection과 혼재 가능"
        ],
    },

    "BENIGN": {
        "behavior": "정상적인 네트워크 트래픽 및 서비스 이용 행위",
        "anchor_techniques": [],
        "tactics": [],
        "notes": [
            "DB 수집/대응 가이드 대상에서 제외. 베이스라인 설명용 메타만 유지"
        ],
    },
}

# KISA 상위 카테고리 / 키워드
## 1024 : 변경된 라벨에 맞게 수정
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

# [날짜 수정: 2026-01-25 web_search 신뢰 도메인 목록 추가]
TRUSTED_SOURCES = [
    ## 해외 사이버보안 뉴스
    "https://www.darkreading.com/",
    ## 국내 사이버보안 뉴스
    "https://www.boannews.com/",
]
