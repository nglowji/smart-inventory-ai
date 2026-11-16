# SmartInventory AI

Ứng dụng quản lý một kho có trợ lý AI chỉ đọc dữ liệu. Hiện triển khai **Phase 0 — Foundation**: backend FastAPI, cấu hình, PostgreSQL, health checks, test và CI. Chưa có API nghiệp vụ, tài khoản, AI hoặc frontend.

## Chạy trên Windows PowerShell

Yêu cầu: Python 3.12+ (đã kiểm thử 3.13), Docker Desktop chạy Linux containers. Chạy từ thư mục gốc repository:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e './backend[dev]'
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
docker compose --env-file .env -f infra/docker-compose.yml up -d --wait
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --app-dir backend --host 127.0.0.1 --port 8000
```

Không cần activate virtualenv hoặc đổi ExecutionPolicy. API chạy trên máy, DB trong Docker. Nếu cổng 5432 đã dùng, đổi POSTGRES_PORT và cổng DATABASE_URL trong .env cho khớp.

- Swagger: http://127.0.0.1:8000/docs
- Liveness: http://127.0.0.1:8000/health → 200 khi API chạy, kể cả DB mất kết nối.
- Readiness: http://127.0.0.1:8000/health/ready → 200 khi DB truy cập được; 503 với DATABASE_UNAVAILABLE khi DB lỗi, không lộ thông tin kết nối.

Readiness hiện kiểm tra kết nối, chưa kiểm tra schema vì chưa có bảng nghiệp vụ. Endpoint này chỉ dùng local và cần bảo vệ trước khi triển khai công khai.

Dừng API bằng Ctrl+C. Dừng DB và giữ dữ liệu:

```powershell
docker compose --env-file .env -f infra/docker-compose.yml stop
```

## Kiểm thử

```powershell
.\.venv\Scripts\python.exe -m ruff check backend
.\.venv\Scripts\python.exe -m pytest backend/tests -q
```

Test PostgreSQL thật sẽ skip nếu thiếu TEST_DATABASE_URL. Để chạy đầy đủ, tạo database test riêng (lệnh createdb chỉ chạy lần đầu):

```powershell
docker compose --env-file .env -f infra/docker-compose.yml exec -T db createdb -U inventory inventory_test
$env:TEST_DATABASE_URL = 'postgresql+psycopg://inventory:local-dev-only@127.0.0.1:5432/inventory_test'
.\.venv\Scripts\python.exe -m pytest backend/tests -q
Remove-Item Env:TEST_DATABASE_URL
```

Nếu đổi user/password/port, cập nhật các lệnh tương ứng. Test gồm cấu hình, OpenAPI, health, lỗi kết nối thật, ẩn credentials trong response và kết nối PostgreSQL thật. GitHub Actions tạo PostgreSQL riêng và chạy lint/test trên push/PR; kết quả CI cần được xác nhận khi workflow thực sự chạy trên GitHub.

## Hiểu code Phase 0

Luồng readiness: Browser → Uvicorn → FastAPI → database_is_ready → SQLAlchemy → psycopg → PostgreSQL (SELECT 1) → HTTP 200/503.

| File | Vai trò | Tương đương ASP.NET Core |
|---|---|---|
| backend/pyproject.toml | Dependencies và cấu hình công cụ | .csproj và cấu hình analyzer/test |
| backend/app/main.py | Tạo app, route, CORS, vòng đời engine | Program.cs, Minimal APIs, middleware |
| backend/app/core/config.py | Đọc .env/environment và kiểm tra cấu hình | Configuration + IOptions validation |
| backend/app/db/connection.py | Connection pool và kiểm tra DB | NpgsqlDataSource và health check |
| backend/tests/ | Unit/smoke và integration tests | xUnit + WebApplicationFactory |
| infra/docker-compose.yml | PostgreSQL, volume, health check | Docker Compose trong dự án .NET |
| .github/workflows/backend.yml | Lint và test tự động | Pipeline restore/build/test |

**What:** Đây là nền tảng backend chạy được, chưa phải ứng dụng kho hoàn chỉnh.

**Why:** Xác nhận cấu hình và DB trước khi thêm nghiệp vụ, giúp phân biệt lỗi hạ tầng với lỗi nhập/xuất.

**How:** Uvicorn là ASGI server nhận HTTP, vai trò gần Kestrel. FastAPI định tuyến request tới hàm Python. Settings đọc environment trước .env. create_app cho phép test truyền cấu hình riêng. lifespan tạo engine lúc app bắt đầu và giải phóng pool khi dừng; engine chỉ mở kết nối khi cần. Đây là cách startup/shutdown được [FastAPI hướng dẫn](https://fastapi.tiangolo.com/advanced/events/). pool_pre_ping kiểm tra kết nối trước khi tái sử dụng theo [SQLAlchemy](https://docs.sqlalchemy.org/en/20/core/pooling.html).

**Trade-offs:** Dùng SQLAlchemy đồng bộ để dễ học transaction. Route def chạy trong thread pool của FastAPI; async def lifespan quản lý vòng đời ASGI, không biến DB driver thành async. Engine là pool dùng chung, khác ORM Session/DbContext; Session theo request và migration sẽ thêm ở Phase 1. Dependencies hiện có khoảng phiên bản, chưa có lockfile cố định toàn bộ cây dependency.

**Đối chiếu .NET:** create_app gần việc tạo WebApplication; decorator application.get gần MapGet; Settings gần IOptions; TestClient tương tự WebApplicationFactory. Python không build IL như C#, nhưng vẫn cần validation, lint và test.

## Giới hạn và bước tiếp theo

- Chưa có bảng, migration, seed user, JWT/RBAC, giao dịch kho, báo cáo hoặc LLM. Không có dữ liệu demo ở Phase 0.
- Compose hiện chỉ chạy PostgreSQL; container backend/frontend bổ sung sau.
- Chưa có HTTPS, backup hoặc cấu hình production; chỉ chạy local.
- .env.example là thông tin mẫu cho local; .env không được commit. Đổi password trong .env sau khi tạo volume không tự đổi password của PostgreSQL.
- Bỏ qua mọi file .md ngoài README.md; skill và đặc tả gốc giữ local theo yêu cầu.
- Phase 1: Category, Supplier, Product, Alembic, tạo sản phẩm kèm balance 0, chuẩn hóa SKU và tests.
- Mỗi phase đều có giải thích What → Why → How → Trade-offs → đối chiếu .NET trước khi chuyển tiếp.
