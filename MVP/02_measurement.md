# 02. Измерение

## Потоки наблюдений

| Источник | Что записывает | Как используется |
|---|---|---|
| `UserPromptSubmit` hook | Текст пользовательского промпта, session/prompt ID если переданы, timestamp | Лента сообщений и prompt-completeness heuristic |
| `Stop` hook | `last_assistant_message` — финальный видимый ответ хода; не streaming output | Лента сообщений; если поле отсутствует, запись отмечается unavailable |
| Другие Claude Code hooks | Тип события, session ID, tool name/result category если доступны | Лента активности, не task progress |
| StatusLine JSON | Context window size, input token total, input-only `used_percentage`, remaining percentage и доступная `current_usage` разбивка | Timestamped context samples; значения null/absent показываются как unavailable |
| Snake task verifiers | Результат проверки каждого требования `q_i` | Единственный источник verifier-backed `D_completion` |

Hooks не предоставляют context token fields. StatusLine — отдельный локальный источник; его `used_percentage` считает входные токены и не включает output tokens.

## Проверенный прогресс

Для каждого требования `i` verifier возвращает `q_i ∈ [0, 1]` строкой `q=<float>` и exit code 0. При ошибке, timeout, невалидном пути/выводе или ненулевом exit code `q_i = 0` и статус ошибки отображается явно.

```text
Progress = Σ(wᵢ · qᵢ) / Σwᵢ
D_completion = 1 − Progress
G_reached = all(hard_i ⇒ q_i = 1) ∧ Progress ≥ q_min
```

`goal.yaml` задаёт веса, hard constraints, `q_min` и пути к verifiers. Изменение цели во время run нельзя делать молча: используйте новый run/goal version. Hook-события, промпты, ответы, Q_prompt, контекстные samples, коммиты и LOC не меняют `q_i`.

## Prompt-completeness heuristic

Для каждого пользовательского промпта выводятся четыре проверяемых cue flags:

1. цель/action;
2. ограничения;
3. ожидаемый результат/deliverable;
4. acceptance criteria/tests/checks.

```text
Q_prompt = (goal + constraints + deliverable + acceptance_checks) / 4
```

Каждый пункт равен 0 или 1, вес — 0.25. Текущий алгоритм — прозрачная RU/EN keyword heuristic: это оценка наличия признаков полноты, не семантическая оценка правильности, ясности или выполнимости. Показывать score вместе с flags и ограничениями метода. Не использовать LLM-судью/API и не связывать этот score с `D_completion`.

## Хранение и приватность

- `messages.jsonl` содержит только видимые UserPromptSubmit prompts и финальные Stop responses, плюс role/session/prompt/turn IDs, timestamp, truncation/redaction metadata.
- Лимит текста — 64 KiB на сообщение. Более длинное сообщение обрезается с явной меткой; высоконадёжные API keys/tokens/password-like assignments маскируются до записи.
- `events.jsonl` хранит allowlisted session/tool metadata; `context_samples.jsonl` — только разрешённые StatusLine context fields; `snapshots.jsonl` — verifier прогресс и ссылки/сводки наблюдений.
- Все файлы локальны в `experiments/runs/<run_id>/` с ограниченными правами записи; удалить записи можно удалением run directory. Не коммитить их.
- Не сохранять hidden system/developer instructions, chain of thought/reasoning, tool input/output, transcript_path contents, файлы проекта или весь сыро́й hook JSON.

## Ограничения контекстных данных

StatusLine `context_window.current_usage` может быть null до первого API вызова и сразу после compaction; другие context fields тоже могут быть отсутствующими. Сохранять эти случаи как unavailable, не подменять нулём или оценкой. Записываемые данные являются последним доступным снимком окна, а не полной историей семантического контекста, не `D_cost` и не `U_D`.
