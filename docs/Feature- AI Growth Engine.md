# Feature: AI Growth Engine

## Overview

AI Growth Engine là một module mới được tích hợp vào hệ thống hiện tại.

Hệ thống hiện tại đã chịu trách nhiệm:

* Facebook Page Management
* Publishing
* Scheduler
* Comment Reply
* Messenger DM
* Analytics Collection (nếu có)

AI Growth Engine chỉ tập trung vào việc giúp Facebook Page tăng trưởng tự nhiên bằng AI.

Module này không giao tiếp trực tiếp với Facebook API mà sử dụng các service hiện có của hệ thống.

---

# Objectives

Mục tiêu của module:

* Discover content opportunities
* Generate engaging content
* Generate AI media
* Optimize content quality
* Learn from historical performance
* Improve organic growth over time

Các KPI hướng tới:

* Reach
* Engagement
* Followers
* Watch Time
* Reel Completion Rate
* Shares
* Viral Potential

---

# Scope

AI Growth Engine chịu trách nhiệm:

* Trend Discovery
* Topic Ranking
* Content Planning
* Hook Generation
* Content Generation
* Media Generation
* AI Review
* Learning

Không chịu trách nhiệm:

* Facebook Authentication
* Publishing
* Scheduler
* Comment Reply
* Messenger Reply

Các chức năng này sẽ sử dụng service hiện có.

---

# High Level Architecture

```text
                 Existing System

       Publish Service
       Analytics Service
       Scheduler
       Media Storage

                ▲

                │

         AI Growth Engine

                │

     ┌──────────┼──────────┐

     │          │          │

 Trend      Content      Learning

 Engine      Engine       Engine

                │

           AI Gateway

                │

 ┌──────────────┼────────────────────┐

 │              │                    │

Quota      Model Router         Prompt Cache

Manager

 │

Fallback Manager

 │

Cost Optimizer
```

---

# AI Gateway

Tất cả các module AI phải gọi AI Gateway.

Không module nào được gọi trực tiếp OpenAI, Gemini, Claude...

AI Gateway chịu trách nhiệm:

* Provider Management
* Model Routing
* Quota Tracking
* Cost Optimization
* Prompt Cache
* Retry
* Fallback
* Logging
* Metrics

Growth Engine hoàn toàn không biết đang dùng AI provider nào.

---

# Provider Manager

Cho phép cấu hình nhiều AI Provider.

Ví dụ:

* OpenAI
* Anthropic
* Google Gemini
* DeepSeek
* Qwen
* GLM
* Local LLM

Mỗi provider có:

* API Key
* Priority
* Daily Quota
* Monthly Quota
* Cost
* Rate Limit
* Supported Models

---

# Model Router

AI Gateway tự chọn model phù hợp.

Ví dụ

Simple Classification

↓

Small Model

---

Hook Generation

↓

Medium Model

---

Long Script

↓

Best Model

---

Grammar Fix

↓

Cheap Model

Module khác không cần biết.

---

# Quota Manager

Theo dõi quota theo thời gian thực.

Ví dụ:

Daily Quota

Remaining Requests

Remaining Tokens

Reset Time

Quota History

Quota Alert

Nếu provider hết quota.

Tự động chuyển provider khác.

---

# Fallback Strategy

Ví dụ

Gemini

↓

Unavailable

↓

DeepSeek

↓

Unavailable

↓

Qwen

↓

Unavailable

↓

Claude

↓

Unavailable

↓

OpenAI

Không được để workflow bị dừng chỉ vì một provider lỗi.

---

# Cost Optimizer

Mục tiêu:

Giảm tối đa số lần gọi AI.

Nguyên tắc:

Ưu tiên Rule-Based.

Sau đó mới AI.

Ví dụ:

Duplicate Detection

↓

Rule

Grammar

↓

Rule

Keyword Extraction

↓

Rule

Topic Clustering

↓

Embedding

Hook Generation

↓

LLM

Content Generation

↓

LLM

Review

↓

LLM nếu cần

---

# Prompt Cache

Nếu prompt giống nhau.

Không gọi AI.

Ví dụ:

Generate content

Topic = Seoul Cafe

Tone = Friendly

Language = English

Nếu đã tồn tại.

Trả về cache.

---

# Batch Processing

Ưu tiên xử lý theo batch.

Sai

1 Topic

↓

1 Request

Đúng

20 Topics

↓

1 Request

Giảm đáng kể số lần gọi AI.

---

# Functional Modules

## Trend Discovery

Thu thập dữ liệu từ nhiều nguồn.

Ví dụ

* RSS
* Website
* Google Trends
* Reddit
* YouTube
* TikTok
* News
* Internal Knowledge

Không dùng AI.

---

## Topic Ranking

Ưu tiên Rule-Based.

Chỉ dùng AI khi cần.

Điểm đánh giá:

* Trend Score
* Freshness
* Audience Match
* Historical Performance
* Search Interest
* Competition
* Seasonal Score

---

## Content Planner

Quyết định:

* Chủ đề
* Định dạng
* Số lượng bài
* Lịch ưu tiên

Dựa trên:

* Analytics
* Learning
* Configuration

---

## Hook Generator

Sinh nhiều Hook.

Ví dụ

20 Hook

↓

AI tự đánh giá

↓

Chọn 3 Hook tốt nhất

↓

Trả về 1 Hook

Chỉ dùng một lần gọi AI.

---

## Content Generator

Sinh:

* Facebook Post
* Caption
* Reel Script
* CTA
* Hashtags

Không publish.

Chỉ trả về Draft.

---

## Media Generator

Sinh:

* Thumbnail
* AI Image
* Cover
* Reel Storyboard
* Reel Video

Có thể sử dụng:

* AI Image
* AI Video
* Stock Assets
* Existing Assets

---

## AI Review

Kiểm tra:

Grammar

Brand Consistency

Duplicate

Sensitive Content

Readability

Engagement Prediction

Nếu không đạt.

Regenerate.

---

## Publish Request

Sau khi hoàn thành.

Module tạo Publish Job.

Publish Service hiện tại sẽ xử lý việc đăng.

---

## Analytics Collector

Đọc dữ liệu từ hệ thống hiện tại.

Ví dụ

Reach

Views

Watch Time

Shares

Comments

Followers

CTR

Completion Rate

Không lấy dữ liệu trực tiếp từ Facebook nếu đã có service.

---

## Learning Engine

Sau mỗi bài.

Lưu:

Topic

Hook

Prompt Version

Media Style

Publish Time

Reach

Engagement

Followers

Watch Time

Completion Rate

Learning Engine cập nhật trọng số để cải thiện các lần sinh tiếp theo.

Không cần gọi AI.

---

# Page Configuration

Mỗi Facebook Page có cấu hình riêng.

Ví dụ:

* Brand
* Language
* Country
* Target Audience
* Brand Personality
* Tone
* Writing Style
* Emoji Level
* Content Categories
* Preferred Content Types
* Reel Frequency
* Posting Strategy
* Image Style
* Video Style
* Thumbnail Style
* CTA Style
* Prompt Templates
* Preferred Trend Sources
* Competitors
* Forbidden Topics
* Blocked Keywords
* LLM Preference
* Image Model
* Video Model
* TTS Provider
* Quality Threshold
* Auto Publish
* Approval Required

Không được hardcode.

---

# Prompt Management

Prompt phải quản lý tập trung.

Ví dụ

Topic Discovery

Hook

Content

Review

Image

Reel

Translation

Prompt có Version.

Có thể chỉnh sửa trên UI.

---

# AI Usage Policy

Để tối ưu quota miễn phí.

Nguyên tắc:

* Không dùng AI nếu Rule-Based đủ tốt.
* Không gọi AI khi đã có cache.
* Ưu tiên Batch Processing.
* Ưu tiên model nhỏ.
* Chỉ dùng model mạnh cho các tác vụ quan trọng.
* Learning Engine không sử dụng AI.
* Analytics không sử dụng AI.
* Trend Discovery không sử dụng AI.

Mục tiêu:

Giảm số lần gọi AI xuống mức tối thiểu.

---

# Learning Strategy

Mỗi bài sau khi publish sẽ tạo Learning Record.

Learning Record bao gồm:

* Topic
* Hook
* Prompt Version
* Model Used
* Publish Time
* Reach
* Engagement
* Shares
* Followers
* Watch Time
* Completion Rate

Learning Engine sử dụng dữ liệu này để tối ưu các lần sinh tiếp theo.

---

# Extensibility

Module phải hỗ trợ:

* Thêm AI Provider mới.
* Thêm AI Model mới.
* Thêm Trend Source mới.
* Thêm Prompt mới.
* Thêm Media Generator mới.
* Thêm Platform mới.
* Thêm Analytics Provider mới.

Không sửa business logic hiện có.

---

# Design Principles

* AI First
* Configuration Driven
* Multi Page
* Multi Language
* Queue Based
* Stateless Worker
* Cost Optimized
* Quota Aware
* Provider Agnostic
* Cache First
* Batch Processing
* Rule Before AI
* Plug-in Architecture

---

# Success Metrics

Module được coi là thành công khi:

* Tăng Organic Reach.
* Tăng Followers.
* Tăng Engagement.
* Tăng Reel Performance.
* Tăng Watch Time.
* Giảm AI Cost.
* Giảm AI Requests.
* Tận dụng tối đa quota miễn phí.
* Chất lượng nội dung được cải thiện liên tục thông qua Learning Engine.
