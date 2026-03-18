# UI Integration Plan - AI Inbox Management System

## Overview
This document outlines the integration plan for connecting the React UI (`d:\email_auto\ui`) with the AI Inbox Management backend system.

---

## Current Architecture

### Backend Components
- **Main Polling Loop**: `main.py` - Polls Gmail and processes emails through LangGraph pipeline
- **Enterprise MCP Server**: `enterprise-mcp-server/` - FastAPI server on port 9000 providing Gmail MCP tools
- **Agent Pipeline**: 7 specialized agents (AG-01 through AG-07) orchestrated via LangGraph
- **Database**: PostgreSQL with tables: `emails`, `audit_log`, `attachments`, `tenants`, `analytics_snapshots`
- **Task Queue**: Celery + Redis for SLA monitoring and background tasks

### Frontend Components (Existing)
- **EmailInbox.tsx**: Main inbox view with real-time SSE updates
- **ChatInterface.tsx**: AI chat interface (currently using Gemini directly)
- **Sidebar.tsx**: Navigation and session management
- **orchestratorService.ts**: Service layer for backend communication (currently pointing to port 8001)

---

## Required Backend API Endpoints

### 1. Email Management API (`/api/v1/emails`)

#### `GET /api/v1/emails`
**Purpose**: Fetch paginated email list with filtering
```typescript
Query Parameters:
- page: number (default: 1)
- limit: number (default: 20)
- status: 'intake' | 'classification' | 'routing' | 'response' | 'audit' | 'human_review' | 'dead_letter'
- priority: 'high' | 'medium' | 'low'
- category: string (from taxonomy)
- tenant_id: string
- date_from: ISO timestamp
- date_to: ISO timestamp
- search: string (searches subject, sender, body)

Response:
{
  "status": "OK",
  "data": {
    "emails": [
      {
        "email_id": "uuid",
        "external_id": "gmail_message_id",
        "source": "gmail",
        "sender": "user@example.com",
        "subject": "Subject line",
        "received_at": "2026-03-14T10:30:00Z",
        "case_reference": "CASE-20260314-abc123",
        "current_step": "classification",
        "classification_result": {
          "category": "billing",
          "priority": "high",
          "confidence": 0.92,
          "sentiment_score": -0.3
        },
        "routing_decision": "Finance Ops",
        "sla_deadline": "2026-03-14T14:30:00Z",
        "elapsed_time": 120.5,
        "ack_sent": true,
        "low_confidence_flag": false,
        "escalated": false
      }
    ],
    "pagination": {
      "total": 150,
      "page": 1,
      "limit": 20,
      "total_pages": 8
    }
  }
}
```

#### `GET /api/v1/emails/{email_id}`
**Purpose**: Get detailed email information including full body, attachments, and audit trail
```typescript
Response:
{
  "status": "OK",
  "data": {
    "email_id": "uuid",
    "external_id": "gmail_message_id",
    "source": "gmail",
    "tenant_id": "acme_corp",
    "sender": "user@example.com",
    "subject": "Subject line",
    "body": "Full email body text...",
    "thread_id": "gmail_thread_id",
    "received_at": "2026-03-14T10:30:00Z",
    "case_reference": "CASE-20260314-abc123",
    "ack_sent": true,
    "attachment_paths": ["/attachments/case-123/file.pdf"],
    "classification_result": {...},
    "sentiment_score": -0.3,
    "confidence": 0.92,
    "low_confidence_flag": false,
    "routing_decision": "Finance Ops",
    "assignment_id": "SNOW-12345",
    "draft": "Draft response text...",
    "pii_scan_result": {
      "is_safe": true,
      "detected_types": [],
      "blocked": false
    },
    "sla_deadline": "2026-03-14T14:30:00Z",
    "elapsed_time": 120.5,
    "alert_80_sent": false,
    "escalated": false,
    "current_step": "response",
    "agent_statuses": {
      "AG-01": "completed",
      "AG-02": "completed",
      "AG-03": "completed",
      "AG-04": "running"
    },
    "pipeline_timings": {
      "intake_at": "2026-03-14T10:30:00Z",
      "classification_at": "2026-03-14T10:30:15Z",
      "routing_at": "2026-03-14T10:30:30Z"
    },
    "audit_trail": [
      {
        "agent_id": "AG-01",
        "event_type": "email_ingested",
        "timestamp": "2026-03-14T10:30:00Z",
        "payload": {...}
      }
    ]
  }
}
```

#### `POST /api/v1/emails/{email_id}/reassign`
**Purpose**: Manually reassign email to different team
```typescript
Request Body:
{
  "team": "Tier 2 Engineering",
  "reason": "Requires escalation"
}

Response:
{
  "status": "OK",
  "message": "Email reassigned successfully"
}
```

#### `POST /api/v1/emails/{email_id}/approve-draft`
**Purpose**: Approve and send AI-generated draft
```typescript
Request Body:
{
  "edited_draft": "Optional edited version of draft"
}

Response:
{
  "status": "OK",
  "message": "Email sent successfully"
}
```

#### `POST /api/v1/emails/{email_id}/reject-draft`
**Purpose**: Reject draft and request human intervention
```typescript
Request Body:
{
  "reason": "Tone inappropriate for customer"
}

Response:
{
  "status": "OK",
  "message": "Draft rejected, routed to analyst queue"
}
```

---

### 2. Dashboard & Analytics API (`/api/v1/analytics`)

#### `GET /api/v1/analytics/dashboard`
**Purpose**: Get real-time dashboard metrics
```typescript
Query Parameters:
- tenant_id: string
- date_from: ISO timestamp
- date_to: ISO timestamp

Response:
{
  "status": "OK",
  "data": {
    "overview": {
      "total_emails": 1250,
      "processed_today": 87,
      "avg_response_time_minutes": 45.2,
      "sla_compliance_rate": 0.94,
      "auto_send_rate": 0.62
    },
    "by_status": {
      "intake": 5,
      "classification": 12,
      "routing": 8,
      "response": 23,
      "human_review": 15,
      "completed": 1187
    },
    "by_priority": {
      "high": 45,
      "medium": 320,
      "low": 885
    },
    "by_category": {
      "billing": 234,
      "it": 456,
      "hr": 123,
      "complaint": 67,
      "query": 370
    },
    "sla_alerts": {
      "at_80_percent": 8,
      "breached": 2
    },
    "sentiment_distribution": {
      "positive": 450,
      "neutral": 650,
      "negative": 150
    }
  }
}
```

#### `GET /api/v1/analytics/trends`
**Purpose**: Get time-series trend data for charts
```typescript
Query Parameters:
- metric: 'volume' | 'response_time' | 'sla_compliance' | 'sentiment'
- granularity: 'hour' | 'day' | 'week' | 'month'
- date_from: ISO timestamp
- date_to: ISO timestamp

Response:
{
  "status": "OK",
  "data": {
    "metric": "volume",
    "granularity": "day",
    "data_points": [
      {
        "timestamp": "2026-03-01T00:00:00Z",
        "value": 87
      },
      {
        "timestamp": "2026-03-02T00:00:00Z",
        "value": 92
      }
    ]
  }
}
```

---

### 3. Agent Status & Monitoring API (`/api/v1/agents`)

#### `GET /api/v1/agents/status`
**Purpose**: Get real-time status of all agents
```typescript
Response:
{
  "status": "OK",
  "data": {
    "agents": [
      {
        "agent_id": "AG-01",
        "name": "Intake Agent",
        "status": "running",
        "last_activity": "2026-03-14T10:35:00Z",
        "processed_count": 1250,
        "error_count": 3,
        "avg_processing_time_ms": 450
      },
      {
        "agent_id": "AG-02",
        "name": "Classification Agent",
        "status": "running",
        "last_activity": "2026-03-14T10:35:05Z",
        "processed_count": 1248,
        "error_count": 5,
        "avg_processing_time_ms": 1200,
        "llm_provider": "groq",
        "rate_limit_remaining": 25
      }
    ],
    "system_health": {
      "polling_loop": "running",
      "celery_worker": "running",
      "celery_beat": "running",
      "database": "connected",
      "redis": "connected",
      "mcp_server": "running"
    }
  }
}
```

---

### 4. Configuration & Settings API (`/api/v1/config`)

#### `GET /api/v1/config/domains`
**Purpose**: Get list of available domain configurations
```typescript
Response:
{
  "status": "OK",
  "data": {
    "domains": [
      {
        "domain_id": "it_support",
        "display_name": "IT Support",
        "taxonomy": ["password_reset", "hardware_issue", ...],
        "routing_teams": ["Tier 1 Support", "Tier 2 Engineering"],
        "auto_send_allowed": true
      }
    ]
  }
}
```

#### `GET /api/v1/config/tenants`
**Purpose**: Get list of tenants (multi-tenant support)
```typescript
Response:
{
  "status": "OK",
  "data": {
    "tenants": [
      {
        "tenant_id": "acme_corp",
        "name": "ACME Corporation",
        "domain_id": "it_support",
        "active": true,
        "created_at": "2026-01-01T00:00:00Z"
      }
    ]
  }
}
```

---

### 5. Real-Time Updates (Server-Sent Events)

#### `GET /api/v1/events/stream`
**Purpose**: SSE stream for real-time email processing updates
```typescript
Event Types:
- email_ingested
- email_classified
- email_routed
- email_drafted
- sla_alert
- agent_status_change

Event Format:
event: email_classified
data: {
  "email_id": "uuid",
  "case_reference": "CASE-20260314-abc123",
  "category": "billing",
  "priority": "high",
  "confidence": 0.92,
  "timestamp": "2026-03-14T10:30:15Z"
}
```

---

## Required UI Pages & Components

### 1. **Dashboard Page** (`/dashboard`)
**Components Needed**:
- `DashboardOverview.tsx` - KPI cards (total emails, SLA compliance, avg response time)
- `EmailVolumeChart.tsx` - Time-series chart showing email volume trends
- `CategoryDistribution.tsx` - Pie/bar chart of email categories
- `SLAMonitor.tsx` - Real-time SLA alerts and breach warnings
- `AgentHealthPanel.tsx` - Status indicators for all 7 agents

**API Calls**:
- `GET /api/v1/analytics/dashboard`
- `GET /api/v1/analytics/trends`
- `GET /api/v1/agents/status`
- SSE: `/api/v1/events/stream`

---

### 2. **Inbox Page** (`/inbox`) - **EXISTING, NEEDS UPDATE**
**Current State**: Already implemented in `EmailInbox.tsx`
**Required Changes**:
1. Update API endpoint from `http://localhost:9000/api/v1/gmail/search` to `/api/v1/emails`
2. Add filtering by `current_step`, `priority`, `category`
3. Display `case_reference` instead of Gmail message ID
4. Show agent pipeline status badges
5. Add SLA countdown timer for each email
6. Implement click-through to email detail view

**New Props/State**:
```typescript
interface EmailListItem {
  email_id: string;
  case_reference: string;
  sender: string;
  subject: string;
  received_at: string;
  current_step: string;
  classification_result: {
    category: string;
    priority: string;
    confidence: number;
  };
  sla_deadline: string;
  elapsed_time: number;
  escalated: boolean;
}
```

---

### 3. **Email Detail Page** (`/inbox/:email_id`)
**Components Needed**:
- `EmailHeader.tsx` - Sender, subject, case reference, received time
- `EmailBody.tsx` - Full email content with attachments
- `ClassificationPanel.tsx` - Category, priority, confidence, sentiment
- `RoutingPanel.tsx` - Assigned team, routing reason, assignment ID
- `DraftPreview.tsx` - AI-generated draft with approve/reject buttons
- `PIIScanResults.tsx` - PII detection results and warnings
- `AgentTimeline.tsx` - Visual pipeline showing which agents have processed
- `AuditTrail.tsx` - Chronological log of all agent actions

**API Calls**:
- `GET /api/v1/emails/{email_id}`
- `POST /api/v1/emails/{email_id}/approve-draft`
- `POST /api/v1/emails/{email_id}/reject-draft`
- `POST /api/v1/emails/{email_id}/reassign`

---

### 4. **Human Review Queue** (`/review`)
**Purpose**: Dedicated page for emails flagged for human review (confidence < 0.7)
**Components Needed**:
- `ReviewQueue.tsx` - List of emails awaiting human review
- `ReviewCard.tsx` - Card showing email + classification + confidence score
- `ConfidenceIndicator.tsx` - Visual gauge for confidence level
- `ManualClassification.tsx` - Form to manually override classification

**API Calls**:
- `GET /api/v1/emails?status=human_review`
- `POST /api/v1/emails/{email_id}/manual-classify`

---

### 5. **SLA Monitor Page** (`/sla`)
**Purpose**: Real-time SLA tracking and breach management
**Components Needed**:
- `SLAOverview.tsx` - Compliance rate, active alerts, breaches
- `SLAAlertList.tsx` - List of emails at 80% SLA threshold
- `SLABreachList.tsx` - List of emails that breached SLA
- `SLATimeline.tsx` - Visual timeline showing SLA windows

**API Calls**:
- `GET /api/v1/emails?sla_alert=true`
- `GET /api/v1/emails?sla_breached=true`
- SSE: `/api/v1/events/stream` (filter for `sla_alert` events)

---

### 6. **Agent Monitor Page** (`/agents`)
**Purpose**: Real-time monitoring of all 7 agents
**Components Needed**:
- `AgentGrid.tsx` - Grid of agent status cards
- `AgentCard.tsx` - Individual agent status, metrics, health
- `AgentLogs.tsx` - Recent logs from selected agent
- `LLMQuotaMonitor.tsx` - Track Groq/Gemini/Mistral rate limits

**API Calls**:
- `GET /api/v1/agents/status`
- `GET /api/v1/agents/{agent_id}/logs`
- SSE: `/api/v1/events/stream` (filter for `agent_status_change`)

---

### 7. **Settings Page** (`/settings`) - **EXISTING, NEEDS EXPANSION**
**Current State**: Basic settings modal
**Required Additions**:
1. **Domain Configuration**: Select active domain (IT Support, Healthcare, etc.)
2. **Tenant Management**: Switch between tenants (multi-tenant support)
3. **LLM Provider Settings**: Configure API keys, rate limits
4. **SLA Thresholds**: Adjust SLA buckets and alert thresholds
5. **Auto-Send Rules**: Configure which categories allow auto-send
6. **Notification Preferences**: Slack channels, email alerts

**API Calls**:
- `GET /api/v1/config/domains`
- `GET /api/v1/config/tenants`
- `PUT /api/v1/config/settings`

---

### 8. **Analytics Page** (`/analytics`)
**Components Needed**:
- `AnalyticsDashboard.tsx` - Comprehensive analytics view
- `VolumeChart.tsx` - Email volume over time
- `ResponseTimeChart.tsx` - Average response time trends
- `SentimentChart.tsx` - Sentiment distribution over time
- `CategoryBreakdown.tsx` - Category distribution pie chart
- `TeamPerformance.tsx` - Performance metrics by routing team

**API Calls**:
- `GET /api/v1/analytics/dashboard`
- `GET /api/v1/analytics/trends?metric=volume`
- `GET /api/v1/analytics/trends?metric=response_time`
- `GET /api/v1/analytics/trends?metric=sentiment`

---

## Updated Service Layer

### Create `emailService.ts`
```typescript
// ui/services/emailService.ts
const API_BASE = 'http://localhost:9000/api/v1';

export class EmailService {
  async getEmails(filters: EmailFilters): Promise<EmailListResponse> {
    const params = new URLSearchParams(filters as any);
    const response = await fetch(`${API_BASE}/emails?${params}`);
    return response.json();
  }

  async getEmailDetail(emailId: string): Promise<EmailDetailResponse> {
    const response = await fetch(`${API_BASE}/emails/${emailId}`);
    return response.json();
  }

  async approveDraft(emailId: string, editedDraft?: string): Promise<void> {
    await fetch(`${API_BASE}/emails/${emailId}/approve-draft`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ edited_draft: editedDraft })
    });
  }

  async rejectDraft(emailId: string, reason: string): Promise<void> {
    await fetch(`${API_BASE}/emails/${emailId}/reject-draft`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reason })
    });
  }

  async reassignEmail(emailId: string, team: string, reason: string): Promise<void> {
    await fetch(`${API_BASE}/emails/${emailId}/reassign`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ team, reason })
    });
  }

  // SSE stream for real-time updates
  subscribeToUpdates(onEvent: (event: EmailEvent) => void): EventSource {
    const eventSource = new EventSource(`${API_BASE}/events/stream`);
    eventSource.onmessage = (event) => {
      onEvent(JSON.parse(event.data));
    };
    return eventSource;
  }
}

export const emailService = new EmailService();
```

### Create `analyticsService.ts`
```typescript
// ui/services/analyticsService.ts
const API_BASE = 'http://localhost:9000/api/v1';

export class AnalyticsService {
  async getDashboard(filters: DateRangeFilter): Promise<DashboardData> {
    const params = new URLSearchParams(filters as any);
    const response = await fetch(`${API_BASE}/analytics/dashboard?${params}`);
    return response.json();
  }

  async getTrends(metric: string, granularity: string, filters: DateRangeFilter): Promise<TrendData> {
    const params = new URLSearchParams({ metric, granularity, ...filters } as any);
    const response = await fetch(`${API_BASE}/analytics/trends?${params}`);
    return response.json();
  }
}

export const analyticsService = new AnalyticsService();
```

### Create `agentService.ts`
```typescript
// ui/services/agentService.ts
const API_BASE = 'http://localhost:9000/api/v1';

export class AgentService {
  async getAgentStatus(): Promise<AgentStatusResponse> {
    const response = await fetch(`${API_BASE}/agents/status`);
    return response.json();
  }

  async getAgentLogs(agentId: string, limit: number = 50): Promise<AgentLogsResponse> {
    const response = await fetch(`${API_BASE}/agents/${agentId}/logs?limit=${limit}`);
    return response.json();
  }
}

export const agentService = new AgentService();
```

---

## Updated Navigation Structure

### Sidebar Menu Items
```typescript
const menuItems = [
  { path: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { path: '/inbox', icon: Inbox, label: 'Inbox', badge: unreadCount },
  { path: '/review', icon: AlertCircle, label: 'Human Review', badge: reviewCount },
  { path: '/sla', icon: Clock, label: 'SLA Monitor', badge: slaAlertCount },
  { path: '/agents', icon: Activity, label: 'Agent Status' },
  { path: '/analytics', icon: BarChart3, label: 'Analytics' },
  { path: '/settings', icon: Settings, label: 'Settings' },
];
```

---

## Implementation Phases

### Phase 1: Backend API Development (Week 1-2)
1. Create FastAPI router for `/api/v1/emails` endpoints
2. Implement email list, detail, and action endpoints
3. Add SSE endpoint for real-time updates
4. Create analytics aggregation queries
5. Add agent status monitoring endpoints

### Phase 2: Service Layer Update (Week 2)
1. Create `emailService.ts`, `analyticsService.ts`, `agentService.ts`
2. Update existing `orchestratorService.ts` to use new endpoints
3. Implement SSE subscription logic
4. Add TypeScript types for all API responses

### Phase 3: Core UI Pages (Week 3-4)
1. Update existing `EmailInbox.tsx` to use new API
2. Create `EmailDetail.tsx` page
3. Create `Dashboard.tsx` page
4. Create `HumanReviewQueue.tsx` page

### Phase 4: Monitoring & Analytics (Week 5)
1. Create `SLAMonitor.tsx` page
2. Create `AgentMonitor.tsx` page
3. Create `Analytics.tsx` page
4. Implement real-time SSE updates across all pages

### Phase 5: Polish & Testing (Week 6)
1. Add loading states and error handling
2. Implement optimistic UI updates
3. Add toast notifications for actions
4. End-to-end testing
5. Performance optimization

---

## Environment Configuration

### Backend `.env` (already exists)
```bash
# API Server
API_PORT=9000
API_HOST=0.0.0.0

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/inbox_mgmt

# Redis
CELERY_BROKER_URL=redis://localhost:6379/0

# LLM Providers
GROQ_API_KEY=...
GOOGLE_API_KEY=...
MISTRAL_API_KEY=...

# Gmail
GMAIL_CLIENT_ID=...
GMAIL_CLIENT_SECRET=...
```

### Frontend `.env.local` (update)
```bash
VITE_API_BASE_URL=http://localhost:9000/api/v1
VITE_SSE_URL=http://localhost:9000/api/v1/events/stream
VITE_GEMINI_API_KEY=... # Keep for direct chat feature
```

---

## Testing Strategy

### Backend API Tests
- Unit tests for each endpoint
- Integration tests for email pipeline
- Load tests for SSE streaming
- Database query performance tests

### Frontend Tests
- Component unit tests (Jest + React Testing Library)
- Integration tests for service layer
- E2E tests (Playwright) for critical flows:
  - Email ingestion → classification → routing → response
  - Human review workflow
  - SLA alert handling

---

## Security Considerations

1. **API Authentication**: Add API key or JWT authentication to all endpoints
2. **CORS Configuration**: Restrict CORS to frontend origin only
3. **Rate Limiting**: Implement rate limiting on all API endpoints
4. **PII Protection**: Never expose raw email bodies with PII in list views
5. **Audit Logging**: Log all user actions (approve, reject, reassign)

---

## Performance Optimization

1. **Database Indexing**: Ensure indexes on `current_step`, `received_at`, `sender`, `case_reference`
2. **Pagination**: Always paginate email lists (max 50 per page)
3. **Caching**: Cache dashboard metrics for 30 seconds
4. **SSE Throttling**: Batch SSE events to avoid overwhelming frontend
5. **Lazy Loading**: Load email body and attachments only on detail view

---

## Next Steps

1. **Immediate**: Create FastAPI router file `enterprise-mcp-server/app/api/routers/v1/emails.py`
2. **Immediate**: Update `EmailInbox.tsx` to use new `/api/v1/emails` endpoint
3. **Week 1**: Implement all email management endpoints
4. **Week 1**: Create `EmailDetail.tsx` page
5. **Week 2**: Implement SSE streaming for real-time updates
6. **Week 2**: Create `Dashboard.tsx` page

---

## Questions to Resolve

1. Should we keep the existing chat interface (`ChatInterface.tsx`) or integrate it into email detail view?
2. Do we need multi-tenant switching in the UI, or is single-tenant sufficient for MVP?
3. Should SLA alerts trigger browser notifications (Notification API)?
4. Do we need offline support (Service Workers) for the UI?
5. Should we implement WebSocket instead of SSE for bidirectional communication?

---

**Document Version**: 1.0  
**Last Updated**: 2026-03-14  
**Author**: AI Assistant  
**Status**: Draft - Awaiting Review
