# Long-Term Memory Architecture (Phương án A)

> Kiến trúc memory dài hạn cho AI companion / AI agent, chạy nhẹ trên VM nhỏ (1 vCPU / 1GB RAM), **không self-host LLM**, không phụ thuộc service vector ngoài.
> Tài liệu này độc lập với dự án — copy sang project khác và dùng lại được.

---

## 1. Ý tưởng cốt lõi

Bot "nhớ lâu dài" **không** bằng cách nhồi lại toàn bộ lịch sử chat vào prompt (đắt + vượt context). Thay vào đó tách **2 tầng lưu trữ**:

| Tầng | Lưu gì | Mục đích | Đặc tính |
|---|---|---|---|
| **1. Transcript thô** (`messages`) | MỌI tin nhắn nguyên văn | Truy vết, context hội thoại ngắn hạn | Append-only, rẻ, có thể rotate |
| **2. Long-term memory** (`memories`) | Fact chắt lọc + embedding | Recall xuyên session với prompt nhỏ gọn | Có phân loại, chấm điểm, khử trùng lặp, decay |

Khả năng nhớ thật sự nằm ở **Tầng 2**. Tầng 1 chỉ là "băng ghi âm" — có thể xóa bớt mà bot vẫn nhớ.

---

## 2. Luồng dữ liệu

```
User message
   ↓
[1] Lưu raw vào messages (verbatim)
   ↓
[2] Retrieve memories liên quan  ──► vector search (sqlite-vec) + ranking
   ↓
[3] Build prompt (system + personality + summaries + memories + history + message)
   ↓
[4] Gọi LLM → reply
   ↓
[5] Lưu reply vào messages
   ↓
[6] (ASYNC, qua queue) Extract memory ──► Score ──► Dedupe ──► Store (+embedding)
```

Bước 6 chạy **bất đồng bộ** (BullMQ / job queue) để không làm chậm phản hồi cho user.

---

## 3. Vì sao SQLite + `sqlite-vec` (không Qdrant/Pinecone/pgvector)

- **In-process:** vector search chạy ngay trong SQLite, không thêm service/RAM.
- **Hợp VM nhỏ:** SQLite disk-based, không nạp hết vào RAM. Mỗi query chỉ quét vector của **1 user**.
- **Zero ops:** 1 file `.db`, backup = copy file.
- **Có đường nâng cấp:** ẩn sau interface `MemoryStore` → sau này đổi sang pgvector/Qdrant/MemPalace mà không sửa phần còn lại.

---

## 4. Schema

### Bảng quan hệ (ORM quản lý, ví dụ Prisma)

```
messages(id, conversation_id, role, content, tokens, created_at)
memories(
  id, user_id,
  type,            -- semantic | episodic | emotional | relationship
  content,
  importance,      -- 1..100
  reason,
  hit_count,       -- số lần được recall / lặp lại
  archived,
  created_at, updated_at, last_decay_at
)
```

### Bảng vector (extension sqlite-vec, cùng file DB, kết nối better-sqlite3 riêng)

```sql
CREATE VIRTUAL TABLE vec_memories USING vec0(
  memory_id TEXT PRIMARY KEY,
  embedding float[256]          -- dim cố định, mock & model thật interchangeable
);
```

> **Lưu ý 2 connection 1 file:** bật `PRAGMA journal_mode=WAL` + `busy_timeout`, ghi memory qua 1 worker single-concurrency để tránh tranh khóa.

---

## 5. Memory Extraction (Tầng 2)

Sau mỗi lượt hội thoại, gọi LLM với prompt trích xuất, trả **JSON only**:

```json
{
  "memories": [
    { "type": "semantic", "content": "Thích ăn phở", "importance": 0, "reason": "" }
  ]
}
```

### Phân loại
- **semantic** — fact (món ăn yêu thích, nghề nghiệp).
- **episodic** — sự kiện đời (đổi việc, chuyển nhà).
- **emotional** — khoảnh khắc cảm xúc mạnh (chia tay, dự án căng thẳng).
- **relationship** — cột mốc giữa AI ↔ user (lần đầu trò chuyện, kỷ niệm 100 ngày).

---

## 6. Importance Scoring (1–100)

```
importance = emotional_intensity (0–40)
           + future_usefulness   (0–30)
           + repetition          (0–20)
           + uniqueness          (0–10)
```

### Save / Ignore rules
- **Lưu khi:** `importance ≥ 60` **HOẶC** emotional event **HOẶC** user preference.
- **Luôn lưu:** major life event, strong emotion, repeated preference, long-term goal, family/career info.
- **Không lưu:** greetings, thanks, acknowledgements, weather comments, casual jokes, duplicated facts.

| Khoảng | Ý nghĩa |
|---|---|
| 1–20 | Bỏ qua |
| 21–40 | Giá trị thấp |
| 41–59 | Tạm thời |
| 60–79 | Lưu |
| 80–100 | Lưu + ưu tiên retrieval |

---

## 7. Dedupe (chống trùng lặp)

Trước khi insert: `findSimilar()` chạy vector search trên memory của user.
- Nếu **cosine similarity > 0.90** → **update** memory cũ (giữ content dài hơn, bump `hit_count`, lấy `max(importance)`) thay vì tạo row mới.
- Ngược lại → tạo memory mới.

---

## 8. Retrieval (trước mỗi câu trả lời)

Lấy 4 nhóm, gộp & khử trùng theo id, **tối đa 30**:
- 10 recent · 10 important · 5 emotional · 5 relationship.

### Ranking score
```
score = 0.40 * semantic_similarity
      + 0.30 * recency
      + 0.20 * (importance / 100)
      + 0.10 * relationship_relevance
```
Sắp giảm dần → cắt theo context budget.

---

## 9. Consolidation (cron hằng đêm ~02:00)

1. **Merge duplicates** — pairwise vector search từng user.
2. **Decay** — mỗi tuần `importance *= 0.98`; **miễn trừ** emotional & relationship; gate bằng `last_decay_at ≥ 7 ngày`.
3. **Sinh summary** — `profile_summary` (≤1500 chars) + `relationship_summary` (≤1500 chars) bằng LLM tier cao.
4. **Archive** — khi user > 10.000 memory, archive thấp điểm nhất; **không bao giờ** xóa `importance > 85` trừ khi user yêu cầu.

---

## 10. Phân tích dung lượng (1000 DAU)

Giả định mỗi user ~40 tin/ngày, ~2 memory/ngày. Embedding 256 chiều = 1KB/memory.

| Hạng mục | / ngày | / năm |
|---|---|---|
| `messages` (~400B/tin) | ~16 MB | **~5.8 GB** |
| `memories` (~1.5KB/memory) | ~3 MB | **~1.1 GB** |
| **Tổng** | ~19 MB | **~7 GB** |

→ Thoải mái với SSD 20GB. RAM 1GB ổn vì mỗi query chỉ quét vector của 1 user (tối đa ~10MB).

### Giảm dung lượng (tùy chọn)
- **Rotate transcript thô:** giữ verbatim 30–90 ngày gần nhất, archive/xóa cũ hơn → `messages` co còn ~0.5–1.5GB, bot **vẫn nhớ** (fact đã ở `memories`).
- **Quantize embedding** int8 (256B thay 1KB) nếu cần.
- Dedupe + consolidation đã tự ổn định `memories`, không phình vô hạn.

→ Có rotate: tổng ổn định **~2–3 GB** dù chạy nhiều năm.

---

## 11. Interface trừu tượng (để portable & swap backend)

```ts
interface MemoryRecord {
  id: string; userId: string; type: MemoryType;
  content: string; importance: number; reason?: string;
  createdAt: Date; score?: number;          // điểm ranking khi retrieve
}
interface MemoryCandidate { type: MemoryType; content: string; importance: number; reason?: string; }

interface MemoryStore {
  save(userId: string, c: MemoryCandidate): Promise<MemoryRecord | null>;     // null nếu dedupe/ignore
  search(q: { userId: string; queryText: string; limit?: number }): Promise<MemoryRecord[]>;
  recent(userId: string, n: number): Promise<MemoryRecord[]>;
  byType(userId: string, type: MemoryType, n: number): Promise<MemoryRecord[]>;
  findSimilar(userId: string, text: string): Promise<{ record: MemoryRecord; similarity: number } | null>;
  applyDecay(userId: string): Promise<void>;
  count(userId: string): Promise<number>;
}

interface EmbeddingProvider { embed(text: string): Promise<number[]>; dim: number; }
```

Triển khai:
- `SqliteMemoryStore` — production (ORM + sqlite-vec).
- `MockMemoryStore` — in-memory Map cho test/dev (không cần DB).
- (tương lai) `PgVectorMemoryStore`, `MemPalaceMemoryStore`... — chỉ cần implement cùng interface, **không sửa pipeline**.

**Mock embedding** (chạy không cần API key): hash-seeded PRNG → vector chuẩn hóa, deterministic. Dùng để test toàn pipeline; semantic thật cần embedding model (Gemini `text-embedding-004`, OpenAI...).

---

## 12. Checklist áp dụng vào project mới

- [ ] Tạo bảng `messages` + `memories` + virtual table `vec_memories`.
- [ ] Cài `better-sqlite3` + `sqlite-vec`; load extension lúc boot (có fallback brute-force cosine).
- [ ] Định nghĩa `MemoryStore` + `EmbeddingProvider`; viết `Sqlite*` và `Mock*`.
- [ ] Extraction prompt trả JSON; scorer (40/30/20/10) + save/ignore rules.
- [ ] Dedupe sim>0.90; retrieval 4-bucket + ranking 40/30/20/10 (≤30).
- [ ] Job queue cho extraction async; cron consolidation 02:00.
- [ ] (Khuyến nghị) policy rotate transcript thô N ngày.
```
