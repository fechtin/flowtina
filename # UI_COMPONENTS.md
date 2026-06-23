# UI_COMPONENTS.md

# Flowtina UI Component System

Version: 1.0

Framework

Vue 3

TypeScript

TailwindCSS

shadcn-vue

Responsive

Dark Mode

---

# Design Principles

Reusable

Consistent

Accessible

Responsive

Composable

Minimal

Professional SaaS style

No duplicated UI

---

# Component Structure

```text
components/

ui/

layout/

cards/

tables/

charts/

forms/

dialogs/

feedback/

navigation/

settings/

dashboard/

posts/

providers/

scheduler/
```

---

# Layout Components

## AppLayout

Responsibilities

Sidebar

Header

Content

Footer

---

## AuthLayout

Login

Register

Forgot Password

---

## MobileLayout

Bottom navigation

Drawer menu

---

## Sidebar

Collapsible

Responsive

Search

---

## HeaderBar

Breadcrumb

Theme switch

Language switch

Notifications

Profile menu

---

# Dashboard Components

## StatsCard

Props

title

value

icon

trend

color

Examples

Posts today

AI cost

Success rate

Errors

---

## MetricGrid

Responsive grid

2 columns mobile

4 columns desktop

---

## RecentActivityCard

Recent posts

Recent jobs

Recent errors

---

## HealthStatusCard

Database

Scheduler

AI Provider

Telegram

Facebook

Status indicator

---

# Chart Components

## LineChart

ECharts

---

## BarChart

---

## PieChart

---

## AreaChart

---

## DonutChart

---

## CostChart

AI cost

---

## PostHistoryChart

Posts per day

---

## ProviderUsageChart

OpenAI

Claude

Gemini

DeepSeek

---

# Table Components

## DataTable

Search

Pagination

Sorting

Export CSV

Responsive

---

## ServerSideTable

Large data

---

## FilterBar

Keyword

Date

Status

Provider

---

## TableToolbar

Refresh

Export

Delete

---

# Form Components

## TextInput

---

## PasswordInput

---

## SearchInput

---

## TextArea

---

## NumberInput

---

## EmailInput

---

## UrlInput

---

## SelectBox

Single

Multiple

---

## SwitchInput

---

## SliderInput

Temperature

TopP

---

## DatePicker

---

## TimePicker

---

## CronBuilder

Minute

Hour

Day

Month

Weekday

Live preview

---

# Button Components

## PrimaryButton

---

## SecondaryButton

---

## DangerButton

---

## GhostButton

---

## IconButton

---

# Feedback Components

## Toast

Success

Error

Warning

Info

---

## AlertBanner

---

## LoadingSpinner

---

## SkeletonLoader

---

## EmptyState

---

## ErrorState

---

## ProgressBar

---

# Dialog Components

## ConfirmDialog

---

## DeleteDialog

---

## ProviderTestDialog

---

## PromptPreviewDialog

---

## PostPreviewDialog

---

## SettingsDialog

---

## UploadDialog

---

# Navigation Components

## Breadcrumb

---

## Tabs

---

## DropdownMenu

---

## LanguageSwitcher

---

## ThemeSwitcher

---

## NotificationBell

Unread counter

---

## UserMenu

---

# Authentication Components

## LoginForm

---

## RegisterForm

---

## ForgotPasswordForm

---

## ChangePasswordForm

---

# Provider Components

## ProviderCard

Model

Status

Latency

---

## ProviderSelector

---

## ModelSelector

---

## ProviderTestButton

---

# Prompt Components

## PromptEditor

Monaco Editor

Syntax highlight

Variables

---

## VariablePanel

---

## PromptVersionTable

---

## PromptPreview

---

# Source Components

## RSSCard

---

## URLCard

---

## KeywordCard

---

## SourceStatusBadge

---

# Scheduler Components

## JobCard

---

## JobHistoryTable

---

## CronExpressionBuilder

---

## NextRunCard

---

## ManualRunButton

---

# Post Components

## PostCard

---

## PostEditor

Markdown

---

## PostPreview

---

## PostStatusBadge

Draft

Published

Failed

---

## VersionHistoryTable

---

## RetryButton

---

# Facebook Components

## PageCard

---

## TokenStatusCard

---

## PublishHistoryTable

---

## InsightCard

---

# Telegram Components

## BotConfigCard

---

## TestMessageButton

---

## ReportCard

---

# Report Components

## DailyReportCard

---

## WeeklyReportCard

---

## ExportButton

---

# Settings Components

## ThemeSettings

---

## LanguageSettings

---

## ProviderSettings

---

## RetrySettings

---

## TimezoneSettings

---

# Notification Components

## NotificationItem

---

## NotificationList

---

## MarkReadButton

---

# Plugin Components

## PluginCard

---

## PluginMarketplace

Future

---

## PluginHealthBadge

---

# Upload Components

## ImageUploader

---

## CSVUploader

---

## TxtUploader

---

# Status Components

## StatusBadge

Success

Warning

Error

Running

Disabled

---

## HealthBadge

Healthy

Degraded

Offline

---

# Theme Rules

Dark Mode

Default

Persist in localStorage

No page reload

---

# Responsive Rules

Desktop

> =1024px

Tablet

768-1023px

Mobile

<=767px

---

# Icons

lucide-vue

Only one icon library allowed.

---

# Color System

Primary

Secondary

Success

Warning

Danger

Muted

Use Tailwind tokens.

No hardcoded colors.

---

# Animation

Transition only.

No heavy animation.

No unnecessary effects.

---

# Accessibility

Keyboard support

ARIA labels

Focus ring

High contrast

---

# Performance Goals

Initial render

<2 seconds

Bundle size

<1MB

Reusable everywhere

No duplicated component

---

# Absolute Rules

Composition API only.

TypeScript strict.

Reusable components.

No inline styles.

No duplicated UI.

Dark mode support.

Production-ready only.
