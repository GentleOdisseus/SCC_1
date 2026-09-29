# 01. Модель Speedometer

## Тестовый сценарий

Пользователь формулирует промпты, Claude Code разрабатывает Snake в чистом workspace, а SCC Speedometer наблюдает в отдельном терминальном окне. Speedometer не реализует задачу за пользователя и не управляет Claude.

## Четыре раздельных отображения

```text
Verified progress:  Start ─────●────── Goal
Context window:     [██████░░░░] 58% input / 200k
Latest prompt:      Q_prompt 75%  goal✓ constraints✓ deliverable✓ checks·
Conversation:       user prompt → final visible Claude response → events
```

1. **Положение точки** — verifier-backed completion `Progress`.
2. **Индикатор контекста** — StatusLine sample: context window size, input tokens и input-only used percentage; не толщина «качества» и не progress.
3. **Q_prompt** — прозрачный heuristic checklist; его flags и score показываются отдельно.
4. **Лента** — пользовательские prompts, финальные видимые ответы Claude и metadata событий.

## Проверенный прогресс

- `Progress = Σ(wᵢ·qᵢ)/Σwᵢ`; `D_completion = 1 − Progress`.
- Цель — область: все hard constraints пройдены и `Progress ≥ q_min`.
- Только verifiers меняют `q_i` и положение точки. Новые сообщения, tool events, изменения LOC или prompt score сами по себе progress не двигают.
- Cost-to-go `D_cost` и неопределённость `U_D` остаются отдельными частями `D=(D_completion,D_cost,U_D)`; они не вычисляются без валидированных источников.

## Prompt completeness heuristic

`Q_prompt = (goal + constraints + deliverable + acceptance_checks) / 4`, каждый флаг 0/1 с равным весом. Детектируются cue words RU/EN. Score означает только наличие признаков в тексте и не оценивает семантическую правильность, выполнимость или качество результата. Для каждого промпта выводить четыре flags; не использовать Q_prompt для объявления цели достигнутой.

## Контекст и цвета

- Контекст измеряется StatusLine JSON, а не hook payloads. `used_percentage` рассчитан по input tokens и не включает output tokens.
- Отсутствующие/null samples — `не измеряется`; не показывать как 0%.
- **Зелёный/жёлтый/красный статус прогресса** относится только к цели/verifiers: выполнена, ещё не выполнена, провален hard verifier.
- Prompt checklist — самостоятельный индикатор. Не перекрашивать verifier progress по heuristic prompt score.

## Границы ленты

Feed содержит user prompt и финальный видимый ответ Claude на Stop hook; Stop не даёт stream во время генерации. Промпты/ответы локальны, capped at 64 KiB и проходят высоконадёжную secret redaction с явной отметкой truncation. Не записываются скрытые system/developer инструкции, internal reasoning, tool input/output, файлы и transcript. Run-directory удаление — retention control.
