---
description: 이 프로젝트에서 devlog 자동 기록을 켠다
allowed-tools: Bash, Read, Write, Edit, AskUserQuestion
---

`session-manager` 스킬을 읽고, 그 규칙에 따라 **이 프로젝트의 devlog 자동 기록을 켠다**.

handoff(`/jay-new`)와 `/clear` 자동 인계는 이 명령 없이도 동작한다. 이 명령이 필요한 건 devlog뿐인데, 매 턴 파일이 쌓이는 동작이라 명시적 동의 없이 켜지면 안 되기 때문이다.

## 절차

1. 현재 상태를 먼저 확인한다 — `.claude/session/` 존재 여부, devlog 활성 여부, handoff 개수, `.gitignore` 등록 여부. 이미 켜져 있으면 상태만 보고하고 **바꿀 것이 있는지만** 묻는다. 이미 된 걸 다시 하지 않는다.

2. 아직 꺼져 있으면 `AskUserQuestion` 으로 묻는다:
   - **devlog 자동 기록을 켤까?** — 켜면 매 턴의 요청·결과·변경 파일이 `.claude/session/devlog.md` 에 쌓인다. 회고와 트러블슈팅에서 값어치가 나오지만, 짧게 끝나는 프로젝트에는 과하다.
   - `.gitignore` 에 `.claude/session/` 이 아직 없다면 추가할지도 같이 묻는다. 기본은 추가(개인 작업 흐름이라 커밋 로그와 중복되고, devlog가 매 턴 커져 diff를 오염시킨다). 팀과 인계 문서를 공유할 목적이면 빼는 게 맞다.

3. 답에 따라 생성한다:
   ```bash
   mkdir -p .claude/session
   touch .claude/session/devlog.md
   ```
   `.gitignore` 는 이미 항목이 있는지 확인하고 없을 때만 append 한다. 기존 내용은 건드리지 않는다.

4. 결과를 4줄 이내로 보고하고, **훅은 다음 턴부터 기록하므로 이미 지나간 이번 세션 앞부분은 남지 않는다**는 점을 알린다.

끄고 싶어지면 `rm .claude/session/devlog.md` 라고 안내한다. 다만 그건 기존 기록을 지우는 일이라, 남길 게 있으면 먼저 옮기라고 짚어준다.
