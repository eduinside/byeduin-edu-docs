# 에듀서치 문서 저장소

**에듀서치** (byeduin VIVES)에서 사용하는 교육 관련 문서 리포지토리입니다.

## 폴더 구조

```
byeduin-edu-docs/
├── 교육법규/      — 초중등교육법, 교육기본법 등 법령
├── 교육과정/      — 2022 개정 교육과정 등
├── 실무지침/      — 학생평가, 기록 등 실무 지침서
└── 교육청계획/    — 교육청 연간 계획, 공지사항
```

## 파일 업로드 방법 (관리자)

### GitHub 웹 UI
1. 해당 폴더 클릭 (예: `교육법규/`)
2. **Add file** → **Upload files** 클릭
3. `.md` 파일 드래그&드롭
4. **Commit changes** 클릭

### Git 명령
```bash
git clone https://github.com/eduinside/byeduin-edu-docs.git
cd byeduin-edu-docs
cp 문서.md ./교육법규/
git add . && git commit -m "docs: 문서 추가" && git push
```

## 파일명 규칙

- 형식: `주제_연도.md` (선택사항)
- 예시: `초중등교육법.md`, `2022개정_초등_교육과정.md`

---

**관리자**: eduinside | **연동 앱**: https://by.eduin.info/search/
