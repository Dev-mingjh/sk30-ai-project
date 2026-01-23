>  merge 가이드는 오늘 중으로 추가할게요. 일단 브랜치에 코드 올려서 서로 확인하는 용도로 사용합시다

```bash
# 새로운 브랜치 생성 및 이동
git checkout -b '브랜치 이름'

# 변경된 모든 파일 스테이징
git add .

# 커밋 메시지 작성
git commit -m '커밋 내용'

# 원격 저장소(origin)의 해당 브랜치로 푸시
git push origin '브랜치 이름'
