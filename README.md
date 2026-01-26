>  각자 브랜치 작업하는 방법
```bash

=======================================================
# 환경 세팅
# git 가져오고 해당 폴더 이동
git clone -b [브랜치명] [저장소 URL]
cd 'git폴더'

# 가상환경 생성
python -m venv venv

# 가상환경 활성화
source venv/scripts/activate

# 의존성 파일 설치( pip install 한 패키지 requriements.txt에 추가해주세요)
# 추가하는법 ( python -c "import os; cur = set(open('requirements.txt').readlines()) if os.path.exists('requirements.txt') else set(); new = [l + '\n' for l in __import__('subprocess').check_output(['pip', 'freeze']).decode().splitlines() if l + '\n' not in cur]; open('requirements.txt', 'a').writelines(new)") 
python -m pip install --upgrade pip
pip install -r requirements.txt

#  pip install 한 패키지 requriements.txt에 추가해주세요)
python -c "import os; cur = set(open('requirements.txt').readlines()) if os.path.exists('requirements.txt') else set(); new = [l + '\n' for l in __import__('subprocess').check_output(['pip', 'freeze']).decode().splitlines() if l + '\n' not in cur]; open('requirements.txt', 'a').writelines(new)"

========================================================
# 작업세팅
# 새로운 브랜치 생성 및 이동
git checkout -b '브랜치 이름'

# 파일 새로 작성 후 변경된 모든 파일 스테이징
git add .

# 커밋 메시지 작성
git commit -m '커밋 내용'

# 원격 저장소(origin)의 해당 브랜치로 푸시
git push origin '브랜치 이름'

# 각자 feature 브랜치 업데이트된 내용 동기화
git checkout 'feature/(ui, ai, guide) or main'
git pull origin 'feature/(ui, ai, guide) or main'

# 현재 작업중인 branch 유지하면서 상위 브랜치 내용만 업데이트 하고싶은경우
git pull origin 'feature/(ui, ai, guide) or main'
```

> 각자 브랜치에서 작업 후에 feature/(ui, guide, ai)브랜치에 pull request 하고 파트별로 1명이 검토 후에 merge 하고
> main에는 최종으로 작업
