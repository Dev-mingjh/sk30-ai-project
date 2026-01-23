>  각자 브랜치 작업하는 방법
```bash
# 새로운 브랜치 생성 및 이동
git checkout -b '브랜치 이름'

# 변경된 모든 파일 스테이징
git add .

# 커밋 메시지 작성
git commit -m '커밋 내용'

# 원격 저장소(origin)의 해당 브랜치로 푸시
git push origin '브랜치 이름'

# 각자 feature 브랜치 업데이트된 내용 동기화
git checkout 'feature/(ui, ai, guide)'
git pull origin 'feature/(ui, ai, guide)'
```

> 각자 브랜치에서 작업 후에 feature/(ui, guide, ai)브랜치에 pull request 하고 파트별로 1명이 검토 후에 merge 하고
> main에는 최종으로 작업
