# FRONTEND.md

# Flowtina Frontend Architecture

Version: 1.0

Framework:

Vue 3

Language:

TypeScript

Bundler:

Vite

UI:

TailwindCSS

Component Library:

shadcn-vue

State Management:

Pinia

Charts:

ECharts

Internationalization:

vue-i18n

Theme:

Dark / Light

Responsive:

Mobile + Desktop

---

# Design Principles

Modern SaaS UI

Responsive first

Reusable components

Minimal API calls

Lazy loading

Dark mode

Professional dashboard

High performance

---

# Folder Structure

```text
frontend/

src/

assets/

components/

layouts/

pages/

router/

stores/

services/

composables/

i18n/

types/

utils/

plugins/

styles/
```

---

# Layouts

## AuthLayout

Pages

Login

Register

Forgot Password

---

## DashboardLayout

Sidebar

Header

Breadcrumb

Notification Center

Main Content

Footer

---

## Mobile Layout

Drawer Sidebar

Bottom Navigation

Responsive Cards

---

# Router Structure

```text
/

login

register

dashboard

projects

providers

prompts

sources

topics

jobs

posts

facebook

telegram

reports

logs

notifications

settings

profile

plugins
```

---

# Global State (Pinia)

## authStore

User

Access token

Refresh token

Login state

---

## projectStore

Current project

Projects list

---

## settingsStore

Language

Theme

Timezone

Budget

---

## dashboardStore

Charts

Stats

Recent posts

---

## notificationStore

Unread count

Notifications

---

# Shared Components

## AppSidebar

Collapsible

Search

Responsive

---

## AppHeader

Breadcrumb

Language Switch

Theme Switch

Profile Menu

---

## StatsCard

Reusable metric cards

Examples

Posts today

Success rate

AI cost

Token usage

---

## ChartCard

Line chart

Bar chart

Pie chart

Area chart

---

## DataTable

Pagination

Search

Sort

Filters

CSV export

---

## ConfirmDialog

Delete confirmation

---

## ToastNotification

Success

Warning

Error

---

## EmptyState

---

## SkeletonLoader

---

# Authentication Pages

## Login

Email

Password

Remember me

Forgot password

---

## Register

Name

Email

Password

Confirm password

---

## Forgot Password

Email

---

# Dashboard Page

Cards

Posts today

Published

Failed

Success rate

AI cost

Token usage

Charts

Posts per day

Token usage

Execution history

Recent activities

---

# Project Page

CRUD

Search

Pagination

Switch project

---

# AI Provider Page

Supported

OpenAI

Gemini

Claude

DeepSeek

OpenRouter

Ollama

LM Studio

vLLM

Fields

Provider

Base URL

API key

Model

Temperature

Top P

Max Tokens

Test Connection

---

# Prompt Page

List templates

Visual editor

Version history

Live preview

Variable preview

---

# Source Page

Tabs

RSS

URL

Keyword

API

CSV

TXT

Each source:

Enable

Disable

Sync

Delete

---

# Topic Page

Priority

Enable

Disable

Search

---

# Scheduler Page

Cron Builder

Interval Builder

Execution History

Next Run

Manual Run

Enable

Disable

---

# Posts Page

Tabs

Draft

Scheduled

Published

Failed

Archived

Actions

Edit

Publish

Retry

Delete

Version history

Preview

---

# Facebook Page

Connected Pages

Token status

Publish history

Insights

Reconnect

---

# Telegram Page

Bot Config

Chat ID

Test Message

History

Daily Reports

---

# Reports Page

Daily

Weekly

Monthly

Export

Download

Send Telegram

---

# Logs Page

Filters

Level

Date

Module

Search

Download

---

# Notifications Page

Unread

Read

Mark all read

---

# Profile Page

Avatar

Name

Email

Password

Language

Timezone

---

# Settings Page

Theme

Language

Timezone

Budget

Retry count

Default provider

Default model

---

# Plugin Page

Installed Plugins

Marketplace

Enable

Disable

Version

---

# UI Components

## Button

Primary

Secondary

Danger

Ghost

---

## Input

Text

Password

Textarea

Search

---

## Select

Single

Multi

---

## Switch

Boolean settings

---

## Badge

Status

Success

Warning

Error

---

## Tabs

Reusable

---

## Modal

Reusable

---

## Card

Reusable

---

## Dropdown

Reusable

---

# Theme

Light

Dark

Persist in localStorage

---

# Internationalization

Languages

English

Vietnamese

Structure

```json
{
  "dashboard": "Dashboard",
  "posts": "Posts",
  "settings": "Settings"
}
```

No reload required.

---

# Responsive Rules

Desktop

≥1024px

Tablet

768-1023px

Mobile

≤767px

Sidebar auto collapse on mobile.

---

# API Layer

services/

auth.service.ts

project.service.ts

provider.service.ts

post.service.ts

facebook.service.ts

telegram.service.ts

dashboard.service.ts

report.service.ts

settings.service.ts

Axios instance

Interceptor

JWT refresh

Error handling

---

# Loading Strategy

Route lazy loading

Component lazy loading

Skeleton loaders

Avoid blocking UI

---

# Charts

Use ECharts

Line chart

Bar chart

Pie chart

Area chart

Dashboard metrics

AI usage

Posts history

Success ratio

---

# Performance Targets

Initial bundle

<1MB

TTFB

<200ms

First render

<2s

Lighthouse score

> 90

---

# Accessibility

Keyboard navigation

ARIA labels

High contrast support

Responsive text

---

# Absolute Rules

Composition API only

TypeScript strict mode

Reusable components

No duplicated code

No inline API calls

Use Pinia stores

Dark mode support

Production-ready only

No TODO

No mock data
