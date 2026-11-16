# SmartInventory AI

Ứng dụng quản lý **một kho**, giao diện tiếng Việt, dữ liệu PostgreSQL thật. Đã có Foundation, Catalog, nghiệp vụ nhập/xuất/điều chỉnh và dashboard. AI Assistant chưa triển khai.

## Chạy trên Windows PowerShell

Yêu cầu Python 3.12+ (đã kiểm thử 3.13), Node.js 24 và Docker Desktop chạy Linux containers. Chạy từ thư mục gốc:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e './backend[dev]'
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
docker compose --env-file .env -f infra/docker-compose.yml up -d --wait
.\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini upgrade head
# Sinh khóa nếu chưa có, giữ nguyên khóa hiện tại; không in secret.
.\.venv\Scripts\python.exe -c "from dotenv import dotenv_values,set_key; from secrets import token_urlsafe; set_key('.env','JWT_SECRET',dotenv_values('.env').get('JWT_SECRET') or token_urlsafe(48))"
# Chỉ chạy seed khi chưa có Admin, không tự ghi đè tài khoản.
.\.venv\Scripts\python.exe -m app.modules.auth.seed
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --app-dir backend --host 127.0.0.1 --port 8000
```

Ở PowerShell thứ hai:

```powershell
cd D:\IT\smart-inventory-ai\frontend
npm ci
npm run dev
```

- Giao diện: http://127.0.0.1:5173/
- Swagger: http://127.0.0.1:8000/docs
- Liveness: http://127.0.0.1:8000/health
- DB readiness: http://127.0.0.1:8000/health/ready

Không cần activate virtualenv hay thay ExecutionPolicy. Frontend dev proxy chuyển /api tới FastAPI trên cổng 8000, tránh lệch CORS giữa localhost và 127.0.0.1. Proxy không tự có trong production build; triển khai thật cần reverse proxy /api hoặc cấu hình tương đương.

Trên workspace local đã có Admin: xem ADMIN_EMAIL / ADMIN_PASSWORD trong .env. Đăng nhập qua giao diện, không đưa mật khẩu vào Git. Seed ưu tiên environment, sau đó .env, hoặc hỏi tương tác. Không có đăng ký công khai, mật khẩu mặc định hay dữ liệu kho mẫu được tự chèn vào kho thật.

Dừng server bằng Ctrl+C. Dừng DB nhưng giữ dữ liệu:

```powershell
docker compose --env-file .env -f infra/docker-compose.yml stop
```

Nếu cổng 5432 bận, sửa POSTGRES_PORT và cổng DATABASE_URL cho khớp. Đổi password trong .env sau khi volume DB đã tồn tại không tự đổi password trong PostgreSQL.

## Dashboard và giao diện vận hành

Dashboard lấy số liệu qua API, không import fixture hay gán sẵn chỉ số. Nếu DB chưa có hàng, giao diện hiển thị số 0 và trạng thái trống đúng thực tế.

- SKU hoạt động, SKU dưới ngưỡng, giá trị tồn ước tính và số giao dịch trong kỳ.
- Tổng lượng tồn tách riêng PCS/KG/LITER. Không cộng các đơn vị khác nhau.
- Giá trị tồn = tổng on_hand × unit_cost_vnd hiện tại, tính bằng Decimal/NUMERIC ở backend; bao gồm tồn của sản phẩm đã archive để không mất giá trị hàng còn lại.
- SKU hoạt động và cảnh báo chỉ tính sản phẩm active. Cảnh báo yêu cầu min_stock > 0 và on_hand < min_stock.
- Tồn/giá trị/cảnh báo là số liệu **hiện tại**. Bộ lọc ngày chỉ áp dụng cho giao dịch và biểu đồ, không giả lập tồn quá khứ.
- Chọn nhanh 7/30/90 ngày hoặc khoảng ngày tùy chọn tối đa 366 ngày, tính theo giờ Việt Nam.
- Biểu đồ IN/OUT có chọn đơn vị và bảng dữ liệu thay thế; không tính ADJUST_IN/OUT vào dòng nhập/xuất vận hành.
- Từ cảnh báo có thể mở form nhập hàng. Giao dịch thành công tự tải lại dashboard; nút Làm mới tải snapshot mới nhất. Chưa dùng WebSocket hoặc streaming.
- Sản phẩm: tìm tên/SKU, lọc danh mục, hoạt động/ẩn, dưới ngưỡng, phân trang, tạo/sửa/archive và xuất CSV trang hiện tại.
- Danh mục/nhà cung cấp: thêm, sửa, ngừng hoạt động/kích hoạt và phân trang.
- Giao dịch: nhập/xuất/điều chỉnh, lịch sử theo SKU/loại/ngày, số tồn trước/sau, người thực hiện, lý do và CSV trang hiện tại.
- Đăng nhập/đăng xuất, hết hạn phiên, loading/error/empty states. Token chỉ giữ trong sessionStorage của tab.

Admin được sửa Catalog và điều chỉnh kho. Staff được nhập/xuất, không sửa Catalog hoặc điều chỉnh. Viewer chỉ đọc. Giao diện ẩn thao tác không được phép, backend vẫn kiểm tra quyền độc lập.

## Quy tắc nghiệp vụ được bảo vệ

- SKU trim + uppercase, UNIQUE kể cả sản phẩm archived.
- Product và balance 0 được tạo trong một transaction; không có API sửa tồn trực tiếp.
- Số lượng giao dịch > 0, tối đa 3 chữ số thập phân; PCS chỉ nhận số nguyên.
- OUT cần lý do; điều chỉnh cần Admin và lý do từ 10 ký tự.
- IN/OUT/ADJUST cập nhật balance và movement nguyên tử. Lock product trước, sau đó SELECT balance FOR UPDATE; cùng thứ tự với Catalog để chống race khi đổi đơn vị/archive.
- Không âm kho; nếu ghi movement thất bại, cập nhật balance cũng rollback.
- Idempotency-Key UUID bắt buộc khi POST movement. Cùng key + payload + actor trả movement cũ (200); khác nội dung trả 409. UNIQUE constraint xử lý cả retry đồng thời. UI giữ cùng key khi gửi lại cùng nội dung trong form đang mở.
- Posted movement không có API sửa/xóa; sửa sai bằng adjustment.
- Product archived không ghi movement mới. Có bất kỳ lịch sử nào thì không đổi unit, kể cả tồn về 0.
- API truyền số lượng/tiền bằng chuỗi decimal; backend dùng Decimal/NUMERIC. Frontend chỉ định dạng/vẽ biểu đồ, không quyết định tồn hay tính giá trị kho.
- Thời gian lưu UTC, query ranh giới ngày Asia/Ho_Chi_Minh.

## Kiểm thử và CI

```powershell
.\.venv\Scripts\python.exe -m ruff check backend
# Tạo DB test lần đầu; bỏ qua lệnh createdb nếu đã tồn tại.
docker compose --env-file .env -f infra/docker-compose.yml exec -T db createdb -U inventory inventory_test
$env:TEST_DATABASE_URL = 'postgresql+psycopg://inventory:local-dev-only@127.0.0.1:5432/inventory_test'
.\.venv\Scripts\python.exe -m pytest backend/tests -q
Remove-Item Env:TEST_DATABASE_URL
cd frontend
npm run build
```

Cập nhật user/password/port trong TEST_DATABASE_URL nếu cấu hình khác. Nếu thiếu biến này, test PostgreSQL được skip. Fixture Catalog/Inventory yêu cầu DB kết thúc bằng _test, tạo schema riêng từng test, chạy Alembic thật rồi chỉ dọn schema đó; không xóa bảng public. Không dùng SQLite thay cho test lock/concurrency.

Bộ test gồm auth, Catalog, rollback, duplicate SKU đồng thời, concurrent OUT 8+8 từ tồn 10, concurrent retry cùng key, conflict giữa hai sản phẩm, Decimal, role, archive, lịch sử bất biến, dashboard fixture, tách đơn vị và ranh giới nửa đêm Việt Nam. Bộ UAT phải cho giá trị tồn 1.367.000 VND và low stock SP002/SP004. Fixture chỉ tồn tại trong DB test.

GitHub Actions có backend lint/test với PostgreSQL riêng và frontend TypeScript/build. Kết quả CI chỉ xác nhận sau khi workflow thực sự chạy trên GitHub. Kiểm tra local hiện gồm test API, TypeScript/build và HTTP qua proxy; chưa chạy bộ kiểm thử UI tự động trong trình duyệt.

## Hiểu dự án theo luồng xử lý

**What:** React là giao diện; FastAPI nhận request và quyết định nghiệp vụ; PostgreSQL lưu dữ liệu và bảo vệ tính nhất quán.

**Why:** Frontend không phải nguồn sự thật về tồn kho. Hai nhân viên có thể cùng nhìn thấy tồn 10, nên backend phải kiểm tra lại trong transaction trước khi xuất.

**How khi xuất kho:**

```text
React gửi JWT + payload + Idempotency-Key
  → FastAPI xác thực user/role và DTO
  → kiểm tra key đã xử lý
  → khóa product, kiểm tra lại key sau khi chờ lock
  → khóa balance, đọc tồn hiện tại
  → kiểm tra số lượng và không âm kho
  → UPDATE balance + INSERT movement
  → COMMIT cùng transaction
  → React tải lại dashboard/danh sách
```

Nếu hai request OUT 8 từ tồn 10, request thứ hai chờ khóa. Khi được đọc tồn, nó thấy 2 và nhận 409, không tiếp tục dùng số 10 đã nhìn thấy trên UI. Nếu đó là retry cùng key, nó nhận lại movement cũ và không trừ thêm.

**How khi xem dashboard:** React gửi khoảng ngày → reporting module chạy SQL aggregate → nhận số liệu decimal dạng chuỗi và as_of → hiển thị KPI, biểu đồ, cảnh báo. Biểu đồ đổi đơn vị chỉ đổi lớp trình bày; tổng từng đơn vị đã được tính chính xác ở backend. Các KPI trong summary được lấy bằng một SQL statement để dùng cùng snapshot PostgreSQL.

**Trade-offs:** Dùng SQLAlchemy đồng bộ để luồng transaction dễ theo dõi; route def chạy trong thread pool. Tách module nhưng chưa thêm repository abstraction vì quy mô nhỏ. Engine là pool kết nối dùng chung; Session là đơn vị làm việc theo request. Dashboard làm mới khi tải màn hình, ghi thành công hoặc bấm Làm mới; chưa có push thời gian thực.

## File chính và đối chiếu .NET

| File | Trách nhiệm | Gần tương đương ASP.NET Core |
|---|---|---|
| backend/app/main.py | Tạo app, routers, CORS, lifespan | Program.cs, middleware, endpoint mapping |
| backend/app/core/config.py | Đọc/validate environment và .env | Configuration + IOptions |
| backend/app/db/models.py | Entities, FK, unique/check constraints | EF Core Entities + Fluent API |
| backend/app/db/session.py | Session theo request | DbContext scoped |
| backend/alembic/ | Schema version, upgrade/downgrade | EF Core migrations |
| backend/app/modules/catalog/ | DTO, CRUD Catalog, product + balance | DTO, Controller, application service |
| backend/app/modules/inventory/ | Lock, idempotency, transaction, lịch sử | Service + database transaction |
| backend/app/modules/reporting/ | SQL aggregates cho dashboard | LINQ GroupBy / projection / SUM |
| backend/app/modules/auth/ | Login, JWT, role dependencies, seed | Authentication + authorization policies |
| frontend/src/api.ts | HTTP client, JWT, timeout, lỗi | HttpClient + delegating handler |
| frontend/src/screens/ | Màn hình dashboard, Catalog, lịch sử | Razor/Blazor pages/components |
| frontend/src/components/Dialog.tsx | Form lưu thật và key retry | EditForm + validation/service call |

Pydantic DTO là hợp đồng HTTP, không phải entity database. DTO không nhận on_hand, actor_id hay stock_before/after từ client. TypeScript giúp kiểm tra kiểu lúc build, không thay thế validation backend. Alembic migration phải chạy để sửa schema; sửa class Python không tự sửa DB. Auth có JWT không thay thế kiểm tra role.

Mật khẩu lưu hash PBKDF2-SHA256 1.000.000 vòng qua Werkzeug; dùng cách này vì máy Windows hiện chặn DLL Argon2. Server không trả mật khẩu/hash/token trong log lỗi. Tham khảo [SQLAlchemy row locking](https://docs.sqlalchemy.org/en/20/core/selectable.html#sqlalchemy.sql.expression.Select.with_for_update) và [PostgreSQL time zones](https://www.postgresql.org/docs/current/functions-datetime.html).

## Phạm vi còn lại

Chưa có AI Assistant, UI quản trị tài khoản, audit logs tổng quát, refresh token, rate limiting đăng nhập, deployment production, HTTPS, backup và secret management. Lịch sử kho đã lưu actor, thời gian, lý do và số dư trước/sau. Không khẳng định toàn bộ MVP hay production đã hoàn tất.

Compose hiện chỉ chạy PostgreSQL; backend/frontend chạy local. Vite proxy là cấu hình dev. Readiness cần bảo vệ khi triển khai công khai. Dependencies frontend có lockfile; Python hiện dùng khoảng phiên bản.

Theo yêu cầu repository, chỉ README.md được đưa lên Git trong các file Markdown; đặc tả gốc và bộ skill giữ local. .env và các secrets không commit. Mỗi đợt triển khai đều có giải thích What → Why → How → Trade-offs → đối chiếu .NET.
