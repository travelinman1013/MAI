# Task: Final Validation & Integration Testing

**Project**: MAI React Frontend (`/Users/maxwell/Projects/MAI`)
**Goal**: Validate all components work together, run integration tests, and verify production readiness
**Sequence**: 15 of 15 (VALIDATION)
**Depends On**: All previous prompts (01-14) completed

---

## Archon Task Management (REQUIRED)

### Task Info
- **Task ID**: `a1b2c3d4-e5f6-7890-abcd-ef1234567890`
- **Project ID**: `17384994-d1d6-4286-992b-bf82d7485830`

### Create Task First
```bash
curl -X POST "http://localhost:8181/api/tasks" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Final Validation & Integration Testing",
    "description": "Validate all React frontend components, run integration tests, verify production readiness",
    "project_id": "17384994-d1d6-4286-992b-bf82d7485830",
    "status": "todo"
  }'
```

### Update Status
```bash
# Mark as in_progress when starting (use actual task ID from create response)
curl -X PUT "http://localhost:8181/api/tasks/{TASK_ID}" \
  -H "Content-Type: application/json" \
  -d '{"status": "in_progress"}'

# Mark as done when complete
curl -X PUT "http://localhost:8181/api/tasks/{TASK_ID}" \
  -H "Content-Type: application/json" \
  -d '{"status": "done"}'
```

---

## Context

All 14 implementation prompts have been completed. This final validation prompt ensures:

1. **All dependencies are installed** - No missing packages
2. **TypeScript compiles cleanly** - No type errors
3. **All components render** - No runtime errors
4. **Backend APIs respond** - All endpoints functional
5. **Integration works** - Frontend connects to backend
6. **User flows complete** - End-to-end functionality verified

This is a **validation-only** task. Do not write new code unless fixing bugs discovered during testing.

---

## Requirements

### 1. Environment Setup Validation

Verify all services are running:

```bash
# Check Docker services (if using Docker)
docker compose ps

# Or verify individual services:
# PostgreSQL
pg_isready -h localhost -p 5432

# Redis
redis-cli ping

# Qdrant
curl http://localhost:6333/collections

# LM Studio (should be running with a model loaded)
curl http://localhost:1234/v1/models
```

### 2. Backend Validation

```bash
cd /Users/maxwell/Projects/MAI

# Start backend if not running
python -m uvicorn src.main:app --reload --port 8000 &

# Wait for startup
sleep 3

# Test health endpoints
echo "=== Health Checks ==="
curl -s http://localhost:8000/health | jq
curl -s http://localhost:8000/health/detailed | jq

# Test sessions API
echo "=== Sessions API ==="
# Create session
SESSION_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/sessions \
  -H "Content-Type: application/json" \
  -d '{"title": "Validation Test"}')
echo "$SESSION_RESPONSE" | jq
SESSION_ID=$(echo "$SESSION_RESPONSE" | jq -r '.id')

# List sessions
curl -s http://localhost:8000/api/v1/sessions | jq

# Get session
curl -s http://localhost:8000/api/v1/sessions/$SESSION_ID | jq

# Add message
curl -s -X POST http://localhost:8000/api/v1/sessions/$SESSION_ID/messages \
  -H "Content-Type: application/json" \
  -d '{"role": "user", "content": "Test message"}' | jq

# Update session
curl -s -X PATCH http://localhost:8000/api/v1/sessions/$SESSION_ID \
  -H "Content-Type: application/json" \
  -d '{"title": "Updated Test"}' | jq

# Test analytics API
echo "=== Analytics API ==="
curl -s http://localhost:8000/api/v1/analytics/usage | jq
curl -s http://localhost:8000/api/v1/analytics/agents | jq
curl -s http://localhost:8000/api/v1/analytics/models | jq
curl -s http://localhost:8000/api/v1/analytics/summary | jq

# Cleanup test session
curl -s -X DELETE http://localhost:8000/api/v1/sessions/$SESSION_ID
echo "Test session deleted"
```

### 3. Frontend Build Validation

```bash
cd /Users/maxwell/Projects/MAI/frontend

# Install dependencies (if not done)
npm install

# Check for TypeScript errors
echo "=== TypeScript Check ==="
npm run build 2>&1

# If build fails, capture errors
if [ $? -ne 0 ]; then
  echo "BUILD FAILED - Fix errors before continuing"
  exit 1
fi

echo "Build successful!"

# Check for lint errors (if eslint configured)
npm run lint 2>&1 || echo "Lint check skipped or has warnings"
```

### 4. Frontend Component Validation

Start dev server and manually verify each component:

```bash
cd /Users/maxwell/Projects/MAI/frontend
npm run dev &
sleep 3
echo "Frontend running at http://localhost:5173"
```

**Manual Checklist - Open http://localhost:5173 and verify:**

#### Layout & Navigation
- [ ] MainLayout renders with sidebar and header
- [ ] Sidebar shows "MAI" logo and can be toggled with button
- [ ] Header shows model selector, LLM status badge, command button, theme toggle, settings button
- [ ] Routes work: `/`, `/chat/:id`, `/analytics`, `/settings`

#### Chat Interface
- [ ] Chat page loads with empty state message
- [ ] "New Chat" button creates a session
- [ ] Message input has auto-resize textarea
- [ ] Paperclip button opens file picker
- [ ] Drag-drop file upload shows visual feedback
- [ ] Image files show thumbnail previews
- [ ] Document files show icon previews
- [ ] Send button submits message
- [ ] User messages appear right-aligned with avatar
- [ ] Assistant messages appear left-aligned with avatar
- [ ] Copy button appears on message hover
- [ ] Streaming indicator shows while "thinking"

#### Split View
- [ ] Split view button in chat header
- [ ] Split view renders two chat panels
- [ ] Resize handle works between panels
- [ ] Secondary panel can be closed
- [ ] "Open in Split" from session context menu works

#### Sidebar Sessions
- [ ] Sessions grouped by Today, Yesterday, Last 7 Days, Older
- [ ] Groups are collapsible
- [ ] Search filters sessions by title
- [ ] Session item shows title and hover actions
- [ ] Context menu: Rename, Open in Split, Delete
- [ ] Rename dialog works
- [ ] Delete removes session

#### Model & Agent Selection
- [ ] Model selector shows available models
- [ ] Model selector shows connection status badge
- [ ] Agent selector shows available agents
- [ ] Selecting model updates store
- [ ] Selecting agent updates store
- [ ] LLM status badge shows connected/offline

#### Settings Panel
- [ ] Settings dialog opens from header button
- [ ] Four tabs: General, Models, Theme, Shortcuts
- [ ] API Settings shows URL inputs with connection test
- [ ] Model Settings lists models with active indicator
- [ ] Theme Settings has light/dark/system buttons
- [ ] Font size slider updates preview
- [ ] Vim mode toggle works
- [ ] Keyboard shortcuts can be customized
- [ ] Settings persist after page reload

#### Command Palette
- [ ] Opens with Cmd+K (or Ctrl+K)
- [ ] Search filters commands
- [ ] "New Chat" action works
- [ ] "Analytics" action navigates
- [ ] "Settings" action opens dialog
- [ ] Theme switching works
- [ ] Recent chats show and navigate
- [ ] Escape closes palette

#### Analytics Dashboard
- [ ] Analytics page shows stat cards
- [ ] Usage chart renders with data
- [ ] Agent insights doughnut chart renders
- [ ] System health shows service statuses
- [ ] Health status updates periodically
- [ ] Loading skeletons show while fetching

#### Theme & Responsiveness
- [ ] Dark theme applies correctly
- [ ] Light theme applies correctly
- [ ] System theme follows OS preference
- [ ] UI is responsive on smaller screens

### 5. Integration Testing

Test complete user flows:

```bash
# Flow 1: Create chat, send message, verify persistence
echo "=== Flow 1: Chat Creation ==="
# 1. Open http://localhost:5173
# 2. Click "New Chat"
# 3. Send a message
# 4. Refresh page
# 5. Verify session and message persist

# Flow 2: Settings persistence
echo "=== Flow 2: Settings ==="
# 1. Open settings
# 2. Change theme to light
# 3. Change font size
# 4. Refresh page
# 5. Verify settings persist

# Flow 3: Analytics data
echo "=== Flow 3: Analytics ==="
# 1. Create several sessions with messages
# 2. Navigate to /analytics
# 3. Verify charts show data
# 4. Verify system health displays

# Flow 4: Command palette
echo "=== Flow 4: Command Palette ==="
# 1. Press Cmd+K
# 2. Type "dark"
# 3. Select "Dark Mode"
# 4. Verify theme changes
# 5. Press Cmd+K again
# 6. Select a recent chat
# 7. Verify navigation
```

### 6. Error Boundary Testing

Test error handling:

```bash
# Test API error handling
# 1. Stop the backend server
# 2. Try to create a new chat
# 3. Verify graceful error handling
# 4. Restart backend
# 5. Verify recovery

# Test invalid routes
# 1. Navigate to /chat/invalid-id
# 2. Verify redirect to home

# Test network errors
# 1. Open DevTools Network tab
# 2. Enable "Offline" mode
# 3. Try various actions
# 4. Verify error messages appear
# 5. Disable "Offline" mode
# 6. Verify recovery
```

### 7. Performance Check

```bash
cd /Users/maxwell/Projects/MAI/frontend

# Build for production
npm run build

# Check bundle size
du -sh dist/

# Expected: < 2MB total

# Check for large chunks
ls -la dist/assets/*.js

# Look for any chunks > 500KB that might need code splitting
```

---

## Success Criteria

### Backend API Tests (All Must Pass)
```bash
# Run this validation script
cd /Users/maxwell/Projects/MAI

# Health endpoints
curl -sf http://localhost:8000/health > /dev/null && echo "✓ /health" || echo "✗ /health"
curl -sf http://localhost:8000/health/detailed > /dev/null && echo "✓ /health/detailed" || echo "✗ /health/detailed"

# Sessions API
curl -sf http://localhost:8000/api/v1/sessions > /dev/null && echo "✓ GET /sessions" || echo "✗ GET /sessions"
curl -sf -X POST http://localhost:8000/api/v1/sessions -H "Content-Type: application/json" -d '{"title":"test"}' > /dev/null && echo "✓ POST /sessions" || echo "✗ POST /sessions"

# Analytics API
curl -sf http://localhost:8000/api/v1/analytics/usage > /dev/null && echo "✓ GET /analytics/usage" || echo "✗ GET /analytics/usage"
curl -sf http://localhost:8000/api/v1/analytics/agents > /dev/null && echo "✓ GET /analytics/agents" || echo "✗ GET /analytics/agents"
curl -sf http://localhost:8000/api/v1/analytics/models > /dev/null && echo "✓ GET /analytics/models" || echo "✗ GET /analytics/models"
```

### Frontend Build (Must Pass)
```bash
cd /Users/maxwell/Projects/MAI/frontend
npm run build && echo "✓ Build successful" || echo "✗ Build failed"
```

### Manual Verification Checklist

**Critical (Must Pass):**
- [ ] Application loads without console errors
- [ ] Chat messages can be sent and received
- [ ] Sessions persist after page reload
- [ ] Settings persist after page reload
- [ ] Analytics page renders charts
- [ ] Health status displays correctly

**Important (Should Pass):**
- [ ] All theme modes work (light/dark/system)
- [ ] Command palette opens and functions
- [ ] Split view works correctly
- [ ] File uploads show previews
- [ ] Keyboard shortcuts work

**Nice to Have:**
- [ ] Animations are smooth
- [ ] No layout shifts on load
- [ ] Responsive on mobile viewport

---

## Common Issues & Fixes

### Issue: "Module not found" errors
```bash
cd /Users/maxwell/Projects/MAI/frontend
rm -rf node_modules package-lock.json
npm install
```

### Issue: TypeScript path alias errors
Verify `tsconfig.json` has:
```json
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  }
}
```

### Issue: API calls failing with CORS
Verify `vite.config.ts` has proxy configured:
```typescript
server: {
  proxy: {
    '/api': 'http://localhost:8000',
    '/health': 'http://localhost:8000',
  }
}
```

### Issue: Charts not rendering
Ensure Chart.js is registered in `lib/chart.ts` and imported before use.

### Issue: Zustand state not persisting
Check that persist middleware is configured with storage name.

### Issue: Database tables don't exist
```bash
cd /Users/maxwell/Projects/MAI
alembic upgrade head
# Or if not using migrations, check models are imported in main.py
```

---

## Final Documentation

After all validations pass, create completion documentation:

### Update README
Add frontend documentation to project README covering:
- How to start the frontend
- Available routes
- Key features
- Configuration options

### Create Archon Completion Document
```bash
curl -X POST "http://localhost:8181/api/documents" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "MAI React Frontend - Implementation Complete",
    "content": "# MAI React Frontend Implementation Complete\n\n## Summary\nAll 15 tasks completed successfully. Full-featured React dashboard with shadcn/ui, split-view chat, command palette, and analytics.\n\n## Validation Results\n- All backend APIs functional\n- Frontend builds without errors\n- All manual tests passed\n- Integration tests passed\n\n## Features Delivered\n- Chat interface with file uploads\n- Split-view chat\n- Session management with persistence\n- Model and agent selection\n- Comprehensive settings\n- Command palette (Cmd+K)\n- Analytics dashboard with Chart.js\n- System health monitoring\n\n## Tech Stack\n- React 18 + TypeScript + Vite\n- shadcn/ui + Tailwind CSS\n- Zustand state management\n- Chart.js for analytics\n- cmdk for command palette\n- FastAPI backend\n\n## Next Steps\n- Add authentication\n- Implement real LLM integration\n- Add more agent types\n- Performance optimization",
    "project_id": "17384994-d1d6-4286-992b-bf82d7485830",
    "doc_type": "completion"
  }'
```

---

## On Completion

1. **All automated tests pass** - Backend APIs respond correctly
2. **Frontend builds** - No TypeScript or build errors
3. **Manual checklist complete** - All critical items verified
4. **Documentation updated** - README and Archon docs created
5. **Mark Archon task as done**

```bash
curl -X PUT "http://localhost:8181/api/tasks/{TASK_ID}" \
  -H "Content-Type: application/json" \
  -d '{"status": "done"}'
```

---

## Congratulations!

The MAI React Frontend is now fully implemented and validated. The system includes:

- **14 implementation tasks** completed
- **1 validation task** verified
- **Full-stack integration** working
- **Production-ready** code

The frontend is ready for:
- User testing
- Performance optimization
- Feature additions
- Production deployment
