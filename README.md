# 🤖 Auto Post & Comment Bot

Bot Telegram tự động đăng video TikTok lên Facebook Page và comment link affiliate Shopee.

## 📋 Workflow

```
1. Gửi link TikTok + SKU qua Telegram
2. Bot download video TikTok (không watermark)
3. Bot đăng video lên tất cả Facebook Pages
4. Bot tự động comment link affiliate Shopee
5. Bot gửi kết quả về Telegram
```

## 🚀 Cài đặt

### Yêu cầu
- VPS Linux với Docker + Docker Compose
- Telegram Bot Token
- Facebook App + Page Access Tokens

### Bước 1: Clone repo

```bash
git clone https://github.com/your-user/auto-posting-comment.git
cd auto-posting-comment
```

### Bước 2: Tạo Telegram Bot

1. Mở Telegram, tìm [@BotFather](https://t.me/botfather)
2. Gửi `/newbot` và làm theo hướng dẫn
3. Copy **Bot Token** được cung cấp
4. Lấy **User ID** của bạn: gửi `/start` cho [@userinfobot](https://t.me/userinfobot)

### Bước 3: Tạo Facebook App & Lấy Token

#### 3a. Tạo Facebook App
1. Vào [developers.facebook.com](https://developers.facebook.com/)
2. Tạo App mới → chọn loại **"Business"**
3. Ghi lại **App ID** và **App Secret**

#### 3b. Lấy Page Access Token (Long-lived, không hết hạn)

```bash
# 1. Vào Graph API Explorer: https://developers.facebook.com/tools/explorer/
# 2. Chọn App của bạn
# 3. Click "Generate Access Token"
# 4. Chọn permissions: pages_manage_posts, pages_read_engagement, publish_video
# 5. Copy short-lived User Token

# 6. Đổi thành long-lived User Token:
curl "https://graph.facebook.com/v21.0/oauth/access_token?\
grant_type=fb_exchange_token&\
client_id=YOUR_APP_ID&\
client_secret=YOUR_APP_SECRET&\
fb_exchange_token=YOUR_SHORT_LIVED_TOKEN"

# 7. Dùng long-lived User Token để lấy Page Token (không hết hạn):
curl "https://graph.facebook.com/v21.0/me/accounts?\
access_token=YOUR_LONG_LIVED_USER_TOKEN"

# Response sẽ chứa access_token cho mỗi Page — đây là Page Token không hết hạn
```

#### 3c. Chuyển App sang Live Mode
1. Vào App Dashboard → Settings → Basic
2. Thêm Privacy Policy URL (có thể dùng link tạm)
3. Toggle sang **Live** mode

> ⚠️ **Quan trọng**: App phải ở Live mode để bài đăng hiển thị public!

### Bước 4: Cấu hình

```bash
# Copy template config
cp .env.example .env

# Sửa file .env với thông tin của bạn
nano .env
```

Cập nhật các giá trị trong `.env`:

```env
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_ADMIN_IDS=your_telegram_user_id

FB_PAGE1_ID=111111111111111
FB_PAGE1_TOKEN=EAAxxxxxxxxxxxxxxx
FB_PAGE1_NAME=Shop Thời Trang 1

FB_PAGE2_ID=222222222222222
FB_PAGE2_TOKEN=EAAxxxxxxxxxxxxxxx
FB_PAGE2_NAME=Shop Thời Trang 2

FB_APP_ID=333333333333333

COMMENT_DELAY_SECONDS=10
```

### Bước 5: Chuẩn bị file SKU

Sửa file `data/sku_mapping.csv`:

```csv
sku,affiliate_link,product_name
SKU001,https://shope.ee/abc123,Áo thun nam basic
SKU002,https://shope.ee/def456,Quần jean nữ slim fit
SKU003,https://shope.ee/ghi789,Giày sneaker unisex
```

### Bước 6: Chạy bot

```bash
# Build và chạy với Docker Compose
docker compose up -d --build

# Xem logs
docker compose logs -f bot

# Dừng bot
docker compose down
```

## 📱 Cách sử dụng

### Đăng bài
Gửi tin nhắn cho bot trên Telegram với format:

```
https://www.tiktok.com/@shop/video/1234567890
SKU001
Caption tùy chọn cho bài đăng
```

- **Dòng 1**: Link TikTok
- **Dòng 2**: SKU sản phẩm (tìm trong file `sku_mapping.csv`)
- **Dòng 3+** *(tùy chọn)*: Caption/mô tả bài đăng. Nếu bỏ trống sẽ dùng title từ TikTok.

### Commands

| Command | Mô tả |
|---|---|
| `/start` | Giới thiệu bot |
| `/help` | Hướng dẫn chi tiết |
| `/list_sku` | Xem danh sách SKU |
| `/reload_sku` | Reload file SKU mapping |
| `/status` | Trạng thái bot + thống kê |
| `/history` | 10 bài đăng gần nhất |

### Kết quả

Bot sẽ gửi lại kết quả:

```
🎉 Kết quả đăng bài:

✅ Shop Thời Trang 1
   📎 https://facebook.com/...
   💬 Comment: OK
✅ Shop Thời Trang 2
   📎 https://facebook.com/...
   💬 Comment: OK

📦 SKU: SKU001 - Áo thun nam basic
```

## 📁 Cấu trúc project

```
auto-posting-comment/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env.example
├── .env                    ← Bạn tạo từ .env.example
├── data/
│   ├── sku_mapping.csv     ← File SKU mapping
│   └── bot_history.db      ← SQLite database (tự tạo)
├── src/
│   ├── main.py             ← Entry point
│   ├── config.py           ← Config loader
│   ├── bot/
│   │   ├── handlers.py     ← Telegram handlers
│   │   └── keyboards.py    ← Inline keyboards
│   ├── services/
│   │   ├── tiktok.py       ← TikTok downloader
│   │   ├── facebook.py     ← Facebook API
│   │   └── sku_manager.py  ← SKU manager
│   ├── models/
│   │   └── database.py     ← SQLite logging
│   └── utils/
│       └── logger.py       ← Logging config
├── logs/                   ← Log files (tự tạo)
└── downloads/              ← Video tạm (tự tạo + xóa)
```

## 🔧 Troubleshooting

### Bài đăng Facebook chỉ admin thấy
→ Kiểm tra App đã chuyển sang **Live mode** chưa.

### Token hết hạn
→ Page Access Token lấy đúng quy trình (qua long-lived user token → me/accounts) sẽ **không hết hạn**.
→ Token sẽ chỉ bị vô hiệu nếu bạn đổi mật khẩu Facebook hoặc gỡ quyền App.

### Video không download được
→ TikWM API có thể bị rate limit. Bot sẽ tự retry 3 lần.
→ Nếu vẫn lỗi, kiểm tra link TikTok có đúng format không.

### Bot không phản hồi
```bash
docker compose logs -f bot
```
Kiểm tra logs để tìm lỗi.

## 📝 Cập nhật SKU

Sửa file `data/sku_mapping.csv` trực tiếp trên VPS, sau đó gửi `/reload_sku` trên Telegram để reload mà không cần restart bot.

## 📄 License

MIT
