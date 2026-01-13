---

description: "Task list template for feature implementation"
---

# Tasks: [FEATURE NAME]

**Input**: Design documents from `/specs/[###-feature-name]/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: The examples below include test tasks. Tests are OPTIONAL - only include them if explicitly requested in the feature specification.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root
- **Web app**: `backend/src/`, `frontend/src/`
- **Mobile**: `api/src/`, `ios/src/` or `android/src/`
- Paths shown below assume single project - adjust based on plan.md structure

<!-- 
  ============================================================================
  IMPORTANT: The tasks below are SAMPLE TASKS for illustration purposes only.
  
  The /speckit.tasks command MUST replace these with actual tasks based on:
  - User stories from spec.md (with their priorities P1, P2, P3...)
  - Feature requirements from plan.md
  - Entities from data-model.md
  - Endpoints from contracts/
  
  Tasks MUST be organized by user story so each story can be:
  - Implemented independently
  - Tested independently
  - Delivered as an MVP increment
  
  DO NOT keep these sample tasks in the generated tasks.md file.
  ============================================================================
-->

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Create project structure per implementation plan
- [ ] T002 Initialize Python (uv) and Node.js (npm) workspaces
- [ ] T003 [P] Configure linting and formatting (ruff, prettier, ESLint)
- [ ] T004 [P] Setup Docker and docker-compose for local development
- [ ] T005 Setup CI/CD pipeline (.github/workflows) for automated testing

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

Examples of foundational tasks (adjust based on your project):

- [ ] T006 Setup Cosmos DB schema and client initialization in apps/common-py
- [ ] T007 [P] Implement authentication framework (Azure Entra ID / OAuth 2.0) in apps/api
- [ ] T008 [P] Setup API middleware (CORS, logging, error handling) in apps/api/src/api/middleware.py
- [ ] T009 [P] Setup API routing structure and base models in apps/api/src/api/routes/ and src/api/models/
- [ ] T010 Implement health check endpoint GET /health in apps/api/src/api/routes/health.py
- [ ] T011 Create base Pydantic models in apps/common-py for shared entities
- [ ] T012 Setup React app structure and routing in apps/ui/src/
- [ ] T013 [P] Setup shared component library (ui-lib) with base components
- [ ] T014 [P] Setup environment configuration management (apps/api/src/api/config.py, apps/ui/.env)
- [ ] T015 Setup Application Insights integration for observability
- [ ] T016 Create base service classes for Azure integrations (Blob Storage, Service Bus) in apps/common-py

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - [Title] (Priority: P1) 🎯 MVP

**Goal**: [Brief description of what this story delivers]

**Independent Test**: [How to verify this story works on its own]

### Tests for User Story 1 (OPTIONAL - only if tests requested) ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T017 [P] [US1] Unit test for [service] in apps/api/tests/unit/test_[service].py
- [ ] T018 [P] [US1] Integration test for [API endpoint] in apps/api/tests/integration/test_[endpoint].py
- [ ] T019 [P] [US1] Component test for [React component] in apps/ui/src/__tests__/test_[component].tsx

### Implementation for User Story 1

#### Backend Tasks
- [ ] T020 [P] [US1] Create [Entity] model in apps/common-py/src/common/models/[entity].py
- [ ] T021 [P] [US1] Create [Entity] Pydantic schema in apps/api/src/api/models/[entity].py
- [ ] T022 [US1] Implement [Service] in apps/api/src/api/services/[service].py (depends on T020, T021)
- [ ] T023 [US1] Implement [endpoint] route in apps/api/src/api/routes/[resource].py
- [ ] T024 [US1] Add request validation and error handling for [endpoint]
- [ ] T025 [US1] Add logging for user story 1 operations

#### Frontend Tasks
- [ ] T026 [P] [US1] Create [Component] in apps/ui-lib/src/components/[Component].tsx
- [ ] T027 [P] [US1] Create [Page] in apps/ui/src/pages/[Page].tsx (depends on T026)
- [ ] T028 [US1] Add TypeScript types in apps/ui-lib/src/types/[types].ts
- [ ] T029 [US1] Implement API client in apps/ui-lib/src/api/[service].ts
- [ ] T030 [US1] Add error handling and loading states to [Page]
- [ ] T031 [US1] Add accessibility (WCAG 2.1 AA) to components

#### Integration Tasks
- [ ] T032 [US1] Integration test: UI↔API communication for [feature]
- [ ] T033 [US1] Docker build verification for all modified services
- [ ] T034 [US1] Update API documentation (Swagger/OpenAPI comments)

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - [Title] (Priority: P2)

**Goal**: [Brief description of what this story delivers]

**Independent Test**: [How to verify this story works on its own]

### Tests for User Story 2 (OPTIONAL)

- [ ] T035 [P] [US2] Test for [feature] in apps/api/tests/integration/test_[feature].py
- [ ] T036 [P] [US2] Component test for [component] in apps/ui/src/__tests__/test_[component].tsx

### Implementation for User Story 2

#### Backend Tasks
- [ ] T037 [P] [US2] Create [Entity] model in apps/common-py/src/common/models/[entity].py
- [ ] T038 [US2] Implement [Service] in apps/api/src/api/services/[service].py
- [ ] T039 [US2] Implement [endpoint] in apps/api/src/api/routes/[resource].py
- [ ] T040 [US2] Add validation and logging

#### Frontend Tasks
- [ ] T041 [P] [US2] Create [Component] in apps/ui-lib/src/components/[Component].tsx
- [ ] T042 [US2] Implement [feature] in apps/ui/src/pages/[Page].tsx
- [ ] T043 [US2] Add API integration and error handling

#### Background Processing (if needed)
- [ ] T044 [US2] Implement Azure Function trigger in apps/functions/src/functions/[trigger]
- [ ] T045 [US2] Add logging and error handling

**Checkpoint**: User Story 2 complete and integrated with Story 1

---

## Phase 5: Background Processing (if applicable)

**Purpose**: Async tasks and background jobs

Examples:
- [ ] T046 [P] [Background] Create Service Bus queue processing function in apps/functions
- [ ] T047 [P] [Background] Implement document processing pipeline (upload trigger → intelligence → storage)
- [ ] T048 [Background] Add monitoring and alerting for function execution
- [ ] T049 [Background] Integration test for async workflow

---

## Phase 6: Quality Assurance & Finalization

**Purpose**: Testing, documentation, and deployment readiness

- [ ] T050 Run full test suite (API + UI): `uv run pytest` + `npm test`
- [ ] T051 Run coverage report: `uv run pytest --cov=src --cov-report=html` (target ≥70%)
- [ ] T052 Linting: `uv run ruff check .` + `npm run lint`
- [ ] T053 Type checking: `uv run mypy src/` + `npm run type-check`
- [ ] T054 Docker build verification for all services
- [ ] T055 Update README.md with feature documentation
- [ ] T056 Update CHANGELOG.md with changes
- [ ] T057 Create Azure deployment bicep updates if needed (infra/)
- [ ] T058 E2E testing against deployed services
- [ ] T059 Performance testing and optimization
- [ ] T060 Security review (dependencies, CORS, auth, secrets)

**Checkpoint**: All quality gates passed, ready for merge and deployment

---

## Phase 4: User Story 2 - [Title] (Priority: P2)

**Goal**: [Brief description of what this story delivers]

**Independent Test**: [How to verify this story works on its own]

### Tests for User Story 2 (OPTIONAL - only if tests requested) ⚠️

- [ ] T018 [P] [US2] Contract test for [endpoint] in tests/contract/test_[name].py
- [ ] T019 [P] [US2] Integration test for [user journey] in tests/integration/test_[name].py

### Implementation for User Story 2

- [ ] T020 [P] [US2] Create [Entity] model in src/models/[entity].py
- [ ] T021 [US2] Implement [Service] in src/services/[service].py
- [ ] T022 [US2] Implement [endpoint/feature] in src/[location]/[file].py
- [ ] T023 [US2] Integrate with User Story 1 components (if needed)

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - [Title] (Priority: P3)

**Goal**: [Brief description of what this story delivers]

**Independent Test**: [How to verify this story works on its own]

### Tests for User Story 3 (OPTIONAL - only if tests requested) ⚠️

- [ ] T024 [P] [US3] Contract test for [endpoint] in tests/contract/test_[name].py
- [ ] T025 [P] [US3] Integration test for [user journey] in tests/integration/test_[name].py

### Implementation for User Story 3

- [ ] T026 [P] [US3] Create [Entity] model in src/models/[entity].py
- [ ] T027 [US3] Implement [Service] in src/services/[service].py
- [ ] T028 [US3] Implement [endpoint/feature] in src/[location]/[file].py

**Checkpoint**: All user stories should now be independently functional

---

[Add more user story phases as needed, following the same pattern]

---

## Phase N: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] TXXX [P] Documentation updates in docs/
- [ ] TXXX Code cleanup and refactoring
- [ ] TXXX Performance optimization across all stories
- [ ] TXXX [P] Additional unit tests (if requested) in tests/unit/
- [ ] TXXX Security hardening
- [ ] TXXX Run quickstart.md validation

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - May integrate with US1 but should be independently testable
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - May integrate with US1/US2 but should be independently testable

### Within Each User Story

- Tests (if included) MUST be written and FAIL before implementation
- Models before services
- Services before endpoints
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes, all user stories can start in parallel (if team capacity allows)
- All tests for a user story marked [P] can run in parallel
- Models within a story marked [P] can run in parallel
- Different user stories can be worked on in parallel by different team members

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together (if tests requested):
Task: "Contract test for [endpoint] in tests/contract/test_[name].py"
Task: "Integration test for [user journey] in tests/integration/test_[name].py"

# Launch all models for User Story 1 together:
Task: "Create [Entity1] model in src/models/[entity1].py"
Task: "Create [Entity2] model in src/models/[entity2].py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test User Story 1 independently
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo
4. Add User Story 3 → Test independently → Deploy/Demo
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1
   - Developer B: User Story 2
   - Developer C: User Story 3
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
