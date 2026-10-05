# subagents

Clonamic 서브에이전트의 규칙과, 어느 플러그인에도 속하지 않는 독립 서브에이전트를 두는 저장소다.

## 세 가지 층

| 층 | 무엇인가 | 형태 | 예 |
| --- | --- | --- | --- |
| 스킬 | 일 하나를 하는 방법. 무엇인지, 언제 쓰는지, 어떻게 쓰는지와 형식·규칙 | `skills/<name>/SKILL.md` (+ `references/`, `scripts/`, `assets/`) | 개발명세서를 쓰고 승인받는 법 |
| 플러그인 | 한 역할을 위한 배포 단위. 관련 스킬 묶음, 필요하면 코드·MCP·서브에이전트 | `plugin.json` + `skills/` (+ `agents/`) | clonamic-harness |
| 서브에이전트 | 자기만의 컨텍스트에서 정해진 절차를 도는 실행 주체 | `<name>.md` 한 파일 | 독립 검토자 |

- 스킬은 "어떻게 하는지"를 주고, 서브에이전트는 "누가 따로 하는지"를 준다.
- 서브에이전트는 스킬의 절차가 부른다. 스킬을 대신하지 않는다. 언제 부를지, 무엇을 넘길지, 결과를 어떻게 받을지는 스킬에 쓴다.
- 서브에이전트 파일에는 그 실행 주체의 절차와 반환 형식만 쓴다.

## 언제 만드나

모두 맞을 때만 만든다.

- 따로 떨어진 컨텍스트가 결과를 낫게 한다. 예: 작업자의 설명에 끌려가지 않는 독립 검토.
- 절차가 고정돼 있고 입력과 반환 형식을 정할 수 있다.
- 같은 절차를 여러 번 부른다.

만들지 않는다: 일 하나의 방법을 알려 주는 것(스킬로 만든다), 한 번 쓰고 마는 지시, 메인 에이전트가 그대로 해도 같은 결과가 나오는 일.

## 원본 형식

원본은 Markdown + YAML 프런트매터 한 파일이다. Claude Code, Cursor, Grok이 이 형식을 그대로 읽는다. Codex만 TOML을 쓰므로 원본에서 생성한다.

```markdown
---
name: code-reviewer
description: Reviews a change on delegation. Never edits files.
model: inherit
---

You are a code reviewer. Write the fixed procedure and the return format here.
```

- 필수: `name`(kebab-case, 파일 이름과 같게), `description`, 본문.
- 공통 선택: `model: inherit`.
- 호스트별 선택: `tools`(Claude·Grok), `readonly`(Cursor). 모르는 키는 각 호스트가 무시한다.
- 본문의 절차는 영어로, 사용자에게 보이는 출력 형식은 한국어로 쓴다.

## 어디에 두나

| 경우 | 위치 |
| --- | --- |
| 한 플러그인의 절차 일부다(그 플러그인 스킬이 부른다) | 그 플러그인의 `agents/<name>.md` |
| 어느 플러그인에도 속하지 않는다 | 이 저장소의 `agents/<name>.md` |

- 플러그인 안 서브에이전트: Claude·Grok은 `agents/`를 바로 읽고, Cursor는 `.cursor-plugin/plugin.json`이 있을 때 읽는다. Codex는 플러그인 서브에이전트를 읽지 못하므로, 서브에이전트를 부르는 스킬은 순차 대체 절차(메인 에이전트가 같은 절차를 따로 한 번 더 도는 것)를 반드시 적는다.
- 독립 서브에이전트 설치 위치:

| 형식 | 전역 | 프로젝트 |
| --- | --- | --- |
| `.md` | `~/.claude/agents/`, `~/.cursor/agents/`, `~/.grok/agents/` | `.claude/agents/`(세 호스트가 함께 읽는다) |
| `.toml` | `~/.codex/agents/` | `.codex/agents/` |

## Codex 변환

`scripts/build_codex.py`가 `<name>.md`를 Codex용 `<name>.toml`로 바꾼다. Python 3.12 이상, 표준 라이브러리만 쓴다.

- `name`: kebab-case를 snake_case로 바꾼다(`code-reviewer` → `code_reviewer`).
- `description`: 그대로 옮긴다.
- `developer_instructions`: 본문 전체.
- 나머지 키(`model`, `tools`, `readonly`)는 옮기지 않는다.

```bash
python3 scripts/build_codex.py                    # agents/*.md → codex/*.toml
python3 scripts/build_codex.py --check            # 다르거나 없으면 1로 끝난다
python3 scripts/build_codex.py ../plugin/clonamic-harness/agents --out .codex/agents
```

생성한 `.toml`은 손으로 고치지 않는다. 원본 `.md`를 고치고 다시 만든다.

## 구조

```text
subagents/
├── agents/<name>.md        # 독립 서브에이전트 원본 (생길 때 만든다)
├── codex/<name>.toml       # build_codex.py 생성물
├── scripts/build_codex.py
└── tests/test_build_codex.py
```

시험: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test*.py'`
