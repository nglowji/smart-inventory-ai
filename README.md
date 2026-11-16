# SmartInventory AI

Ứng dụng quản lý **một kho**, có trợ lý AI chỉ đọc dữ liệu. Đã triển khai **Phase 0 — Foundation** và **Phase 1 — Catalog**. Chưa có API nhập/xuất, dashboard, AI hoặc frontend.

## Chạy trên Windows PowerShell

Yêu cầu: Python 3.12+ (đã kiểm thử 3.13), Docker Desktop với Linux containers. Chạy từ thư mục gốc repository:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e './backend[dev]'
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
docker compose --env-file .env -f infra/docker-compose.yml up -d --wait
.\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini upgrade head
# Sinh khóa nếu chưa có; giữ nguyên khóa hiện tại, không in secret ra terminal.
.\.venv\Scripts\python.exe -c "from dotenv import dotenv_values,set_key; from secrets import token_urlsafe; set_key('.env','JWT_SECRET',dotenv_values('.env').get('JWT_SECRET') or token_urlsafe(48))"
# Chỉ seed lần đầu. Nhập email và mật khẩu tối thiểu 12 ký tự khi được hỏi.
.\.venv\Scripts\python.exe -m app.modules.auth.seed
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --app-dir backend --host 127.0.0.1 --port 8000
```

Nếu đã có Admin, không cần chạy seed lại; lệnh seed sẽ từ chối ghi đè tài khoản. Seed nhận ADMIN_EMAIL / ADMIN_PASSWORD từ environment, sau đó .env, hoặc hỏi tương tác. Không có đăng ký công khai hay mật khẩu mặc định. Trên workspace hiện tại đã tạo Admin với mật khẩu ngẫu nhiên trong .env; mở file local để xem ADMIN_EMAIL / ADMIN_PASSWORD, không đưa mật khẩu vào Git.

Không cần activate virtualenv hay thay ExecutionPolicy. API chạy trên máy, DB trong Docker. Nếu cổng 5432 đã dùng, đổi POSTGRES_PORT và cổng DATABASE_URL trong .env cho khớp. Đổi password trong .env sau khi volume DB đã tồn tại không tự đổi password trong PostgreSQL.

- Swagger: http://127.0.0.1:8000/docs
- Liveness: http://127.0.0.1:8000/health → 200 khi API chạy, kể cả DB mất kết nối.
- Readiness: http://127.0.0.1:8000/health/ready → 200 khi kết nối DB được; 503 nếu DB lỗi.

Readiness hiện chỉ kiểm tra kết nối, chưa kiểm tra schema. Phải chạy migration trước khi dùng Catalog. API chạy local; readiness cần được bảo vệ trước khi triển khai công khai.

Dừng API bằng Ctrl+C. Dừng DB và giữ dữ liệu:

```powershell
docker compose --env-file .env -f infra/docker-compose.yml stop
```

## Thử Catalog qua Swagger

1. POST /api/v1/auth/login với email/password của Admin.
2. Copy access_token. Bấm Authorize ở Swagger, dán token vào HTTPBearer.
3. POST /api/v1/categories với {"name":"Văn phòng phẩm"}.
4. POST /api/v1/suppliers với tên, phone/email tùy chọn.
5. POST /api/v1/products bằng payload mẫu dưới. Có thể gắn category_id/default_supplier_id từ hai bước trên.
6. GET /api/v1/products và GET /api/v1/products/{id}: tồn bằng 0.000.
7. POST /api/v1/products/{id}/archive: sản phẩm bị ẩn, bản ghi và lịch sử vẫn giữ nguyên.

```json
{
  "sku": " sp001 ",
  "name": "Bút bi xanh",
  "unit": "PCS",
  "min_stock": "10",
  "lead_time_days": 5,
  "unit_cost_vnd": "3500.00"
}
```

SKU được trim và uppercase thành SP001. Tạo lại sp001, kể cả sau archive, trả 409 SKU_ALREADY_EXISTS. Quantity/money dùng JSON string decimal, không gửi float. Không nhận on_hand từ client. Khi sản phẩm đã có bất kỳ movement nào, đổi unit trả 409 UNIT_IMMUTABLE, kể cả tồn hiện tại bằng 0.

Các API hiện có:

| Endpoint dưới /api/v1 | Quyền |
|---|---|
| POST /auth/login | Public |
| GET /auth/me | User hoạt động |
| GET /categories, /suppliers | Admin, Staff, Viewer |
| POST /categories, /suppliers | Admin |
| PATCH /categories/{id}, /suppliers/{id} | Admin |
| GET /products, /products/{id} | Admin, Staff, Viewer |
| POST /products, PATCH /products/{id} | Admin |
| POST /products/{id}/archive | Admin |

Danh sách có page/page_size (tối đa 100); sản phẩm lọc theo search, active và category_id. Category/supplier cũng lọc active. PATCH chỉ sửa trường đã gửi; category_id, supplier_id, phone/email có thể bỏ liên kết bằng null tùy DTO. Không có DELETE vật lý, API sửa balance hoặc API sửa/xóa movement.

## Kiểm thử

```powershell
.\.venv\Scripts\python.exe -m ruff check backend
.\.venv\Scripts\python.exe -m pytest backend/tests -q
```

Không có TEST_DATABASE_URL thì test PostgreSQL được skip. Muốn chạy đầy đủ, tạo database test riêng (createdb chỉ chạy lần đầu):

```powershell
docker compose --env-file .env -f infra/docker-compose.yml exec -T db createdb -U inventory inventory_test
$env:TEST_DATABASE_URL = 'postgresql+psycopg://inventory:local-dev-only@127.0.0.1:5432/inventory_test'
.\.venv\Scripts\python.exe -m pytest backend/tests -q
Remove-Item Env:TEST_DATABASE_URL
```

Cập nhật user/password/port nếu cấu hình local khác. Fixture Catalog yêu cầu tên database kết thúc bằng _test, tạo schema ngẫu nhiên riêng từng test, chạy Alembic thật rồi chỉ dọn schema đó. Không xóa bảng public hoặc dùng SQLite để thay PostgreSQL.

Bộ test kiểm tra: login và 401/403, user bị khóa, JWT hết hạn, validation, chuẩn hóa SKU, duplicate kể cả concurrent create, tạo product + balance nguyên tử, rollback nếu balance lỗi, archive giữ history, khóa unit sau history, lọc/phân trang và migration upgrade/downgrade. GitHub Actions chạy lint và test với PostgreSQL riêng trên push/PR. Chưa coi workflow đạt cho đến khi xác nhận kết quả trên GitHub.

## Hiểu dự án: Phase 0

**What:** FastAPI, cấu hình, connection pool, health và hạ tầng test.

**Why:** Xác nhận API/DB chạy được trước khi thêm nghiệp vụ.

**How:** Uvicorn nhận HTTP, FastAPI gọi route, SQLAlchemy quản lý kết nối, psycopg gửi SQL cho PostgreSQL. Settings ưu tiên environment hơn .env. create_app cho phép test truyền cấu hình riêng. lifespan tạo engine khi app bắt đầu, dispose khi dừng; kết nối chỉ mở lúc cần. pool_pre_ping kiểm tra kết nối trước khi tái sử dụng.

**Trade-offs:** SQLAlchemy đồng bộ giúp dễ theo dõi transaction; route def chạy trong thread pool. async def lifespan quản lý vòng đời ASGI, không biến driver DB thành async. Engine là pool dùng chung, khác Session theo request.

**.NET:** Uvicorn gần Kestrel; create_app gần tạo WebApplication; route decorator gần MapGet/MapPost; Settings gần IOptions.

## Hiểu dự án: Phase 1

**What:** Catalog có dữ liệu thật, migration và quyền tối thiểu. File chính:

| File | Trách nhiệm | Gần tương đương .NET |
|---|---|---|
| backend/app/db/models.py | ORM models, FK, unique/check constraints | EF Core Entities + Fluent API |
| backend/app/db/session.py | Session theo request, đóng/rollback khi lỗi | DbContext scoped |
| backend/app/modules/catalog/schemas.py | DTO và validation request/response | Request DTO + validation |
| backend/app/modules/catalog/api.py | HTTP routes, permissions, query params | Controllers / Minimal APIs |
| backend/app/modules/catalog/service.py | Quy tắc, transaction và mapping dữ liệu | Application service + SaveChanges |
| backend/alembic/versions/0001_catalog_and_minimal_auth_schema.py | Lịch sử thay đổi schema, upgrade/downgrade | EF Core migration |
| backend/app/modules/auth/ | JWT tối thiểu, seed Admin | Authentication + role policy |
| backend/app/core/errors.py | Lỗi thống nhất, không trả SQL/secrets | Exception handler middleware |

**Why tách DTO và model?** DTO là hợp đồng với client, model là cấu trúc lưu trữ. Client không được gửi on_hand/actor_id hay tự gán quyền. Pydantic kiểm tra đầu vào; PostgreSQL constraints tiếp tục bảo vệ khi có request cạnh tranh.

**How một POST product chạy:**

```text
HTTP + JWT
  → xác thực user đang hoạt động và role Admin
  → Pydantic kiểm tra DTO, chuẩn hóa SKU
  → Session kiểm tra FK
  → tạo Product và StockBalance(on_hand=0)
  → flush/commit trong cùng transaction
  → trả ProductRead, decimal dạng chuỗi
```

Session là đơn vị làm việc của ORM, giữ các entity đang theo dõi; Engine là nguồn kết nối. Session tồn tại theo request và chưa tự commit. Service quyết định commit khi hoàn tất toàn bộ thao tác. Nếu INSERT balance lỗi, INSERT product cũng rollback: tránh sản phẩm mồ côi không có tồn.

**Quan hệ:** Một category có nhiều product; một supplier có thể là supplier mặc định của nhiều product. Hai FK trên product được phép null. Một product có đúng một balance ở luồng tạo API; product_id vừa là PK vừa là FK trong stock_balances. Một product có nhiều movement. Bảng movements được chuẩn bị để Catalog kiểm tra đã có lịch sử; nghiệp vụ ghi kho chỉ triển khai Phase 2.

**Migration:** Sửa class Python không tự sửa database. Alembic lưu phiên bản schema qua alembic_version. upgrade head áp dụng migration còn thiếu; không dùng create_all lúc khởi động app. Đã kiểm thử upgrade/downgrade trong schema test riêng. Không chạy downgrade trên dữ liệu thật vì migration này sẽ xóa bảng.

**Quyền:** JWT chỉ chứa định danh user và thời hạn. Backend đọc user/role hiện tại từ DB ở mỗi request; token hợp lệ không đồng nghĩa được sửa dữ liệu. Viewer/Staff đọc Catalog nhưng không tạo/sửa/archive. Mật khẩu dùng PBKDF2-SHA256 với 1.000.000 vòng và salt ngẫu nhiên qua Werkzeug, do Windows hiện tại chặn DLL Argon2. Không lưu mật khẩu thô trong bảng users.

**Trade-offs:** Chưa thêm repository abstraction vì ORM service hiện đủ nhỏ. Tách model/schema/service để dễ kiểm thử mà không tạo quá nhiều lớp. Khóa row product khi patch; Phase 2 phải phối hợp cùng thứ tự khóa khi tạo movement để tránh đua giữa đổi unit/archive và nhập/xuất. Việc kiểm tra SKU trùng dựa cả UNIQUE constraint, không chỉ SELECT trước INSERT.

**.NET:** Session gần DbContext; session.add gần DbSet.Add; commit gần SaveChanges trong transaction; relationship gần navigation property; Alembic gần EF migrations. Pydantic còn thực hiện chuyển kiểu runtime; type hint Python không tự đảm bảo dữ liệu bên ngoài hợp lệ.

Tham khảo chính thức: [Alembic](https://alembic.sqlalchemy.org/en/latest/tutorial.html), [JWT trong FastAPI](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/), [Werkzeug hashing](https://werkzeug.palletsprojects.com/en/stable/utils/#werkzeug.security.generate_password_hash).

## Giới hạn và phase tiếp theo

- Auth hiện là tối thiểu để bảo vệ Catalog, chưa có UI quản trị user, refresh token, rate limiting đăng nhập hoặc audit đầy đủ. Đây là môi trường học local, chưa production-ready.
- Chưa có API IN/OUT/ADJUST, stock history, dashboard, AI, frontend, HTTPS hoặc backup. Compose hiện chỉ có PostgreSQL.
- Dependencies có khoảng phiên bản, chưa có lockfile cố định toàn bộ cây dependency.
- .env không được commit. Mọi file .md ngoài README.md, bộ skill và đặc tả gốc được giữ local theo yêu cầu.
- Phase 2: transactions nhập/xuất/điều chỉnh, row locking, Decimal theo đơn vị, idempotency và test concurrent OUT trên PostgreSQL thật.
- Mỗi phase đều có giải thích What → Why → How → Trade-offs → đối chiếu .NET và điểm dừng trước phase tiếp theo.
