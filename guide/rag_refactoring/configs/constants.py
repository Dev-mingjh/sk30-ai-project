"""라벨/카테고리/키워드 등 공통 상수 정의.

- 라벨 목록: Attack_LABELS
- 라벨→MITRE 매핑: label_to_attack
- 라벨 정규화 alias: LABEL_NORMALIZE_ALIASES
- KISA 카테고리: LABEL_TO_KISA_CATEGORY, KISA_CATEGORY_KEYWORDS_KO
- KISA 문단 분류용 키워드: LABEL_KEYWORDS
- MITRE 베이스 URL: BASE_MITRE_URL
"""
# [날짜 수정: 2026-01-25 rag_v1 상수 분리]
Attack_LABELS = [
    "DDoS",
    "PortScan",
    "Web Attack - Brute Force",
    "FTP-Patator",
    "Bot",
    "BENIGN",
    "Infiltration",
    "DoS slowloris",
]

label_to_attack = {
    "DDoS": {
        "behavior": "대량의 트래픽을 발생시켜 네트워크 또는 서비스의 가용성을 저하시키는 공격 행위",
        "anchor_techniques": ["T1498", "T1498.001", "T1498.002", "T1498", "T1499.001", "T1499.002", "T1499.003", "T1499.004"],
        "tactics": ["Impact"],
        "notes": ["대용량 플러딩, 반사(reflection) 기반 DDoS 포함"],
    },
    "DoS": {
        "behavior": "",
        "anchor_techniques": ["T1498", "T1498.001", "T1498.002", "T1498", "T1499.001", "T1499.002", "T1499.003", "T1499.004"],
        "tactics": ["Impact"],
        "notes": ["L7 slow DoS, 이후 KISA 문서에서 웹서버/서비스거부 대응 섹션과 강하게 결합"],
    },
    "heartbleed": {
        "behavior": "",
        "anchor_techniques": [""],
        "tactics": ["Impact"],
        "notes": ["L7 slow DoS, 이후 KISA 문서에서 웹서버/서비스거부 대응 섹션과 강하게 결합"],
    },
    "PortScan": {
        "behavior": "대상 시스템의 열려 있는 포트 및 서비스 정보를 탐색하기 위한 스캔 행위",
        "anchor_techniques": ["T1046"],
        "tactics": ["Discovery"],
        "notes": ["사전 정찰 단계, IDS/방화벽 로그 분석과 연계"],
    },
    "Web AttackBrute Force": {
        "behavior": "웹 로그인 인터페이스를 대상으로 계정 정보를 반복적으로 추측하는 공격 행위",
        "anchor_techniques": ["T1110", "T1110.001", "T1110.002", "T1110.003", "T1110.004"],
        "tactics": ["Credential Access"],
        "notes": ["로그인 실패 횟수 급증, 계정 잠금 정책 대응"],
    },
    "FTP-Patator": {
        "behavior": "FTP 서비스를 대상으로 사용자 계정 정보를 무차별 대입하는 공격 행위",
        "anchor_techniques": ["T1110", "T1110.001", "T1110.002", "T1110.003", "T1110.004"],
        "tactics": ["Credential Access"],
        "notes": ["프로토콜(FTP)은 메타데이터로 관리 (service=ftp)"],
    },
    "Bot": {
        "behavior": "감염된 호스트가 외부 명령제어 서버와 통신하는 봇넷 기반 행위",
        "anchor_techniques": ["T1110.002"],
        "tactics": ["Command and Control"],
        "notes": ["HTTP/HTTPS 기반 C2면 T1071.001에 태그. DNS면 이후 T1071.004 등으로 확장"],
    },
    "Infiltration": {
        "behavior": "외부 공격자가 내부 네트워크로 침투하여 정보 접근 또는 외부 유출을 시도하는 행위",
        "anchor_techniques": ["T1567", "T1567.002", "T1078", "T1190", "T1204"],
        "tactics": ["Exfiltration"],
        "notes": ["CICIDS 'Infiltration'은 환경에 따라 lateral movement/collection도 섞일 수 있어 추후 보강"],
    },
    "BENIGN": {
        "behavior": "정상적인 네트워크 트래픽 및 서비스 이용 행위",
        "anchor_techniques": [],
        "tactics": [],
        "notes": ["DB 수집 대상(가이드/대응)에서 제외. 베이스라인/정상 설명용 메타로만 유지"],
    },
}

LABEL_NORMALIZE_ALIASES = {
    "DoS Slowloris": "DoS slowloris",
    "dos slowloris": "DoS slowloris",
    "Port Scan": "PortScan",
    "WebAttack-BruteForce": "Web Attack - Brute Force",
    "Web Attack Brute Force": "Web Attack - Brute Force",
    "FTP Patator": "FTP-Patator",
}

LABEL_TO_KISA_CATEGORY = {
    "Web Attack - Brute Force": "계정탈취/인증공격",
    "FTP-Patator": "계정탈취/인증공격",
    "PortScan": "스캔/정찰",
    "DDoS": "서비스거부(DoS/DDoS)",
    "DoS slowloris": "서비스거부(DoS/DDoS)",
    "Infiltration": "침투/내부확산",
    "Bot": "악성코드/봇넷",
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
    "DoS slowloris": ["slowloris", "슬로우리", "느린 요청", "연결 유지", "세션 고갈"],
    "PortScan": ["포트", "스캔", "정찰", "탐색", "nmap"],
    "Web Attack - Brute Force": ["무차별", "대입", "brute", "로그인 실패", "비밀번호", "인증"],
    "FTP-Patator": ["ftp", "patator", "로그인 실패", "비밀번호"],
    "Bot": ["봇넷", "c2", "명령제어", "악성코드", "감염"],
    "Infiltration": ["침투", "내부", "유출", "원격", "확산"],
    "BENIGN": ["정상"],
}

BASE_MITRE_URL = "https://attack.mitre.org"
