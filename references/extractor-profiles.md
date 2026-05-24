# Extractor Profiles

Use extractor profiles to understand what `generate_project_wiki.py` can infer from each technology stack.

## Profiles

- `generic`: file names, module names, risk regexes, and dependency signals.
- `java-spring`: Spring MVC mappings, Java/Kotlin types, services, MyBatis/Mapper/TableName, Rabbit/Kafka listeners, scheduled jobs.
- `node-ts-js`: Express/Fastify-style router calls, NestJS decorators, TypeScript classes/interfaces/types, queue/cache/ORM/client clues.
- `python-web`: FastAPI/Flask route decorators, Django `path`/`re_path`, Python classes/functions, Celery/APScheduler/cache/ORM clues.
- `go-web`: Gin/Echo-style route registrations, Go structs/interfaces/functions, GORM/cache/client clues.
- `frontend-routes`: React/Vue/Next route and component files, API client/cache/state clues.

## Confidence

- `high`: route/controller, service/usecase, domain object, and collaborator/risk evidence are all present.
- `medium`: some evidence is present but the flow boundary is incomplete.
- `low`: inferred mainly from names/signals; phrase claims as "从当前代码未完全确认".

## Extension Guidance

When adding a new stack:

- Add endpoint patterns before adding domain-specific flow names.
- Add type/model extraction so answers can mention real domain objects.
- Add collaborator extraction for queues, jobs, caches, external clients, repositories, and schedulers.
- Keep patterns evidence-oriented; avoid turning dependency names alone into confident implementation claims.
- Preserve the `wiki.json` shape so validators and question-generation instructions remain compatible.
