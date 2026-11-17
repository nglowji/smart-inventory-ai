# SmartInventory AI

Ứng dụng quản lý **một kho**, giao diện tiếng Việt, dữ liệu PostgreSQL thật. Đã có Foundation, Catalog, nghiệp vụ nhập/xuất/điều chỉnh, dashboard, quản trị tài khoản và nhật ký kiểm toán. AI Assistant chưa triển khai.

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
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --app-dir backend --host 127.0.0.1 --port 8000 --no-access-log
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

### Chạy backend bằng Docker trên Windows

Nếu Windows Application Control chặn DLL của `psycopg`, có thể chạy backend trong Linux container. Cấu hình này không thay đổi chính sách Windows. Giữ `.env` hiện tại; lần cài đầu cần điền cấu hình và sinh `JWT_SECRET` như hướng dẫn trên. API đọc secret từ môi trường lúc chạy; `.env` không được đóng vào image.

```powershell
docker compose --env-file .env -f infra/docker-compose.yml --profile api build api
docker compose --env-file .env -f infra/docker-compose.yml --profile api run --rm api python -m alembic -c backend/alembic.ini upgrade head
docker compose --env-file .env -f infra/docker-compose.yml --profile api run --rm api python -m alembic -c backend/alembic.ini check
# Chỉ dùng seed khi chưa có Admin và đã điền ADMIN_PASSWORD trong .env.
# docker compose --env-file .env -f infra/docker-compose.yml --profile api run --rm api python -m app.modules.auth.seed
docker compose --env-file .env -f infra/docker-compose.yml --profile api up -d api
```

Frontend vẫn chạy bằng `npm run dev` và dùng cùng URL/API proxy. Không chạy đồng thời backend Python local và Docker trên cổng 8000. Sau khi sửa backend, build lại image và chạy `up -d api`. Profile `api` là tùy chọn; lệnh Compose cũ vẫn chỉ chạy DB. Container dùng user không phải root và chỉ mở API trên loopback của máy.

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
| frontend/src/shared/api/ | HTTP client, session, timeout, lỗi và phân trang | HttpClient + delegating handler |
| frontend/src/features/ | Màn hình, form và API theo tính năng | Razor/Blazor components theo feature |
| frontend/src/features/operations/ | Chọn form nghiệp vụ cần mở | Điều phối các component nhập liệu |

Pydantic DTO là hợp đồng HTTP, không phải entity database. DTO không nhận on_hand, actor_id hay stock_before/after từ client. TypeScript giúp kiểm tra kiểu lúc build, không thay thế validation backend. Alembic migration phải chạy để sửa schema; sửa class Python không tự sửa DB. Auth có JWT không thay thế kiểm tra role.

Mật khẩu lưu hash PBKDF2-SHA256 1.000.000 vòng qua Werkzeug; dùng cách này vì máy Windows hiện chặn DLL Argon2. Server không trả mật khẩu/hash/token trong log lỗi. Tham khảo [SQLAlchemy row locking](https://docs.sqlalchemy.org/en/20/core/selectable.html#sqlalchemy.sql.expression.Select.with_for_update) và [PostgreSQL time zones](https://www.postgresql.org/docs/current/functions-datetime.html).

## Phạm vi còn lại

Chưa có AI Assistant, refresh token, rate limiting đăng nhập, deployment production, HTTPS, backup và secret management. Lịch sử kho đã lưu actor, thời gian, lý do và số dư trước/sau. Nhật ký kiểm toán ghi các sự kiện được liệt kê trong Phase 3, chưa bao phủ mọi thay đổi dữ liệu. Không khẳng định toàn bộ MVP hay production đã hoàn tất.

Compose chạy PostgreSQL và có profile `api` tùy chọn cho backend; frontend chạy local. Vite proxy là cấu hình dev. Readiness cần bảo vệ khi triển khai công khai. Dependencies frontend có lockfile; Python hiện dùng khoảng phiên bản.

Theo yêu cầu repository, chỉ README.md được đưa lên Git trong các file Markdown; đặc tả gốc và bộ skill giữ local. .env và các secrets không commit. Mỗi đợt triển khai đều có giải thích What → Why → How → Trade-offs → đối chiếu .NET.

## Cấu trúc và quy ước clean code

Frontend tổ chức theo tính năng, dùng lớp app để ghép màn hình và shared cho phần thật sự dùng chung:

```text
frontend/src/
  main.tsx                       # Bootstrap React và font/style
  app/
    App.tsx                      # Cổng xác thực
    Workspace.tsx                # Điều phối màn hình, thao tác, refresh
    navigation.ts                # Screen ID có type, nhãn, quyền nút chính
    components/                  # Sidebar, Topbar, PageHeader, ReportPeriod
  features/
    auth/                        # Đăng nhập, useAuth, API xác thực
    catalog/                     # Products, MasterData, form và API Catalog
    inventory/                   # Giao dịch, lịch sử, bảng, API và tên loại giao dịch
    dashboard/                   # Dashboard, chart và adapter dữ liệu biểu đồ
    operations/                  # Action union và bộ chọn form theo action
  shared/
    api/                         # Client HTTP, lỗi, session, query và pagination
    hooks/                       # useResource, useDebouncedValue
    ui/                          # Modal, feedback, pagination, icon
    lib/                         # Định dạng, ngày, CSV và đọc FormData
    styles/                      # Tokens, base, layout, components, forms, responsive
    contracts.ts                 # DTO và các union type dùng xuyên tính năng
```

Backend giữ cấu trúc module; mỗi file có một vai trò rõ:

```text
backend/app/
  main.py                        # Composition root, kết nối routers
  core/                          # Config, lỗi, thời gian và schema Page chung
  db/                            # Models, connection, session, pagination SQL
  modules/<feature>/
    api.py                       # HTTP route, quyền, parse request, response model
    schemas.py                   # Hợp đồng request/response Pydantic
    queries.py                   # Truy vấn đọc SQLAlchemy
    service.py                   # Nghiệp vụ ghi, transaction và commit
    serializers.py               # Chuyển entity thành dữ liệu trả ra
```

Không bắt buộc tạo đủ mọi file cho mọi feature: chỉ tách khi có trách nhiệm thực tế. Chưa thêm generic repository, mediator, CQRS hay interface không có nhu cầu.

**What:** App chỉ điều phối; feature chứa nghiệp vụ giao diện; shared cung cấp hạ tầng. Router backend không còn tự dựng SQL.

**Why:** Sửa form sản phẩm không phải đọc logic đăng nhập/giao dịch; thay cách gọi API không phải sửa từng bảng; quy tắc hủy request được kiểm soát ở một chỗ.

**How:** Component gọi API của feature → HTTP client chung → backend router → query/service → database. `useResource` quản lý loading/success/error và hủy request khi rời màn hình. Sau khi hủy, kết quả cũ không được cập nhật state. Request 401 cũ cũng không được xóa token của phiên đăng nhập mới.

Mỗi form có component riêng. `FormModal` chỉ quản lý mở/đóng, trạng thái lưu và hiển thị lỗi; không chứa quy tắc sản phẩm hay giao dịch. `MovementForm` sở hữu key retry; `ProductForm` gửi patch có type và chỉ gồm trường thay đổi.

**Trade-offs:** Có thêm file nhưng ít trách nhiệm trong mỗi file. Giữ DTO tại contracts chung và dùng hàm API đơn giản để tránh tạo lớp abstraction thừa. Kiểm tra TypeScript không thay thế validation HTTP; backend response models tiếp tục bảo vệ hợp đồng trả về.

**Đối chiếu .NET:** `App` gần composition root; API feature gần typed HttpClient; hook gần logic trạng thái dùng lại của component; schema gần DTO. Backend `api.py` gần Controller, `service.py` gần Application Service, `queries.py` gần truy vấn projection EF Core. Transaction nhập/xuất vẫn nằm trong inventory service.

Quy tắc bắt buộc cho thay đổi tiếp theo:

- Shared không import ngược app/features. Component feature không gọi HTTP client trực tiếp mà đi qua `api.ts` của feature; ESLint kiểm tra các ranh giới này.
- Screen ID, role, đơn vị và loại giao dịch dùng union type; không dùng chuỗi tùy ý hoặc `any` để né lỗi.
- React hooks phải đúng thứ tự và đủ dependencies. Request tải dữ liệu có AbortSignal, timeout và xử lý lỗi.
- Backend core/db không phụ thuộc feature. Router không chứa SQL; service/query/serializer không import router hoặc FastAPI. Test kiến trúc kiểm tra các quy tắc này.
- Không đổi response field, quyền, transaction, cách tính Decimal hay idempotency khi chỉ refactor cấu trúc.
- Tiền và số lượng trong payload giữ dạng chuỗi decimal. Thay đổi nội dung form không được vô tình gửi lại các FK không đổi.
- Không sửa migration đã áp dụng chỉ để làm đẹp code. Thay đổi schema phải có migration mới.

Kiểm tra frontend từ thư mục frontend:

```powershell
npm run lint
npm run format:check
npm run test
npm run build
```

Chạy `npm run format` để chuẩn hóa định dạng. TypeScript bật strict, noUnusedLocals, noUnusedParameters, noUncheckedIndexedAccess và noFallthroughCasesInSwitch. CI chạy các kiểm tra trên cùng lint/test backend. Test frontend hiện bao phủ phiên đăng nhập cũ, hủy phân trang, lỗi upstream, patch FK, precision tiền, ngày Việt Nam và dữ liệu biểu đồ tách đơn vị.

## Phase 2 — Stock Core: hoàn thiện và nghiệm thu

Các API kho đã được xây khi nối dashboard. Đợt Phase 2 này rà soát theo BR-03…BR-13, BR-20 và TC-09…TC-19, tách policy thuần để test offline, bổ sung kiểm thử còn thiếu và thêm migration `0002` bảo vệ số dư giao dịch ở DB.

### Chức năng được nghiệm thu

| Nhóm | Hành vi |
|---|---|
| Nhập | IN tăng balance, ghi quantity và số dư trước/sau, supplier tùy chọn |
| Xuất | OUT cần lý do; thiếu tồn trả 409 và không ghi giao dịch |
| Điều chỉnh | ADJUST_IN/OUT chỉ Admin, lý do ít nhất 10 ký tự; giảm không vượt tồn |
| Số lượng | Decimal, dương, tối đa 3 số thập phân; PCS phải nguyên |
| Đồng thời | Khóa product rồi balance trong cùng transaction, không âm kho |
| Retry | Cùng key/nội dung/actor trả movement cũ; khác nội dung hoặc actor trả 409 |
| Archive | Không tạo movement mới; retry giao dịch cũ vẫn trả lại kết quả cũ |
| Lịch sử | Lọc SKU, loại, actor và ngày, phân trang; không sửa/xóa posted movement |
| Chống giả mạo | Client không được truyền actor_id, stock_before, stock_after hoặc on_hand |
| Tính nguyên tử | INSERT movement lỗi thì UPDATE balance rollback cùng transaction |

Khi chỉ truyền `date_from`, lịch sử lọc từ đầu ngày Việt Nam đó trở đi; chỉ `date_to` thì lọc tới hết ngày đó. Truyền cả hai giới hạn tối đa 366 ngày. Dashboard tiếp tục dùng khoảng ngày có đủ hai đầu.

### Code mới cần hiểu

- `inventory/policies.py`: quyền ghi, quy tắc quantity và phép cộng/trừ tồn; không phụ thuộc HTTP hoặc SQLAlchemy.
- `inventory/idempotency.py`: fingerprint từ payload đã chuẩn hóa và actor. `5` và `5.000` có cùng ý nghĩa; actor khác không thể nhận lại giao dịch của nhau bằng cùng key.
- `inventory/service.py`: điều phối kiểm tra key, lock, policy, cập nhật balance, ghi movement và commit/rollback.
- `inventory/queries.py`: tra cứu key và đọc tồn/lịch sử; ranh giới ngày nằm ở `core/dates.py`.
- `alembic/versions/0002_movement_balance_delta.py`: CHECK bảo đảm IN/ADJUST_IN có after = before + quantity và OUT/ADJUST_OUT có after = before − quantity. Migration không tự tạo sản phẩm hay giao dịch.

**What:** Một giao dịch kho là hai thay đổi đi cùng nhau: số dư mới và một bản ghi lịch sử. Không được lưu một phần.

**Why:** Transaction chống lưu nửa chừng; row lock chống hai request cùng tính từ một số dư cũ; idempotency chống một thao tác bị ghi hai lần do retry. Ba cơ chế xử lý ba vấn đề khác nhau và đều cần thiết.

**How:** Request có JWT → nhận actor từ token → kiểm tra role và key → khóa product → kiểm tra key lại sau khi chờ lock → khóa balance bằng SELECT FOR UPDATE → tính bằng Decimal → UPDATE balance + INSERT movement → COMMIT. UNIQUE constraint xử lý cả trường hợp hai sản phẩm khác nhau cạnh tranh cùng key; transaction thua phải rollback rồi tra lại movement đã ghi.

Ví dụ: tồn 10, hai request OUT 8. Request đầu khóa và ghi tồn 2. Request sau đọc lại tồn 2 sau khi chờ, nên nhận 409. Nếu request sau là retry cùng key, nó trả movement cũ mà không xuất thêm. Nếu INSERT movement thất bại, tồn quay lại giá trị trước request.

**Trade-offs:** Đây là khóa bi quan, request cùng SKU có thể phải chờ nhau. Với một kho nhỏ, sự rõ ràng và tính đúng đắn quan trọng hơn tối đa throughput. Giữ transaction ngắn, cùng thứ tự lock và không gọi LLM/network ngoài trong khi giữ khóa. Balance giúp đọc nhanh; movement giữ lịch sử truy vết. CHECK ở DB bổ sung bảo vệ nếu code ghi snapshot sai, không thay thế kiểm tra nghiệp vụ.

**Đối chiếu EF Core:** Session gần DbContext; commit gần SaveChanges trong transaction. SELECT FOR UPDATE là khóa bi quan của PostgreSQL, khác optimistic concurrency dùng rowversion/concurrency token: optimistic phát hiện xung đột khi ghi rồi yêu cầu xử lý lại, còn cách hiện tại chờ khóa trước khi đọc/tính tồn.

### Chạy và kiểm thử Phase 2

```powershell
# Từ thư mục gốc, áp dụng migration mới.
.\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini upgrade head
.\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini check
.\.venv\Scripts\python.exe -m ruff check backend

# Unit tests policy/idempotency không cần DB hoặc network.
.\.venv\Scripts\python.exe -m pytest backend/tests/test_inventory_policies.py -q

# Database test riêng phải được tạo như hướng dẫn ở trên.
$env:TEST_DATABASE_URL = 'postgresql+psycopg://inventory:local-dev-only@127.0.0.1:5432/inventory_test'
.\.venv\Scripts\python.exe -m pytest backend/tests -q
Remove-Item Env:TEST_DATABASE_URL
```

Thử trên UI: thêm SKU PCS → Nhập 30 → Xuất 18 với lý do → kiểm tra tồn 12 và history 0→30→12 → thử xuất 13 để thấy lỗi thiếu tồn. Những bước này dùng dữ liệu bạn chủ động nhập; automated tests luôn chạy trong schema test riêng.

Phase 2 đã nghiệm thu Stock Core; phần tiếp theo bổ sung quản trị tài khoản và kiểm toán. Không lưu mật khẩu thực trong README hoặc Git.

## Phase 3 — Quản trị tài khoản, phiên đăng nhập và kiểm toán

Phiên bản 0.4.0 bổ sung màn hình **Tài khoản**, **Nhật ký hoạt động** cho Admin và chức năng **Đổi mật khẩu** cho người đang đăng nhập. Dashboard tiếp tục đọc số liệu từ PostgreSQL; không tạo tài khoản hay giao dịch giả để lấp giao diện.

| API (tiền tố `/api/v1`) | Quyền và chức năng |
|---|---|
| `GET /users` | Admin tìm email và phân trang tài khoản |
| `POST /users` | Admin tạo tài khoản ADMIN/STAFF/VIEWER |
| `PATCH /users/{id}` | Admin đổi role, bật/tắt tài khoản hoặc đặt lại mật khẩu |
| `POST /auth/change-password` | Người dùng xác nhận mật khẩu hiện tại để đổi mật khẩu của mình |
| `GET /audit` | Admin xem nhật ký, lọc sự kiện, ngày, actor và phân trang |

Mật khẩu mới dài 12–128 ký tự. API không trả password hash. Không có đăng ký công khai. Hệ thống ngăn vô hiệu hóa hoặc hạ quyền Admin hoạt động cuối cùng; transaction advisory lock tuần tự hóa các thay đổi quản trị để hai request đồng thời không cùng vượt qua kiểm tra này.

**Phiên đăng nhập:** JWT xác định người dùng; backend đọc tài khoản trong DB để kiểm tra role, trạng thái và `auth_version`. Đổi mật khẩu, đặt lại mật khẩu, đổi role hoặc trạng thái sẽ tăng phiên bản và vô hiệu hóa các token cũ. Bật lại tài khoản không khôi phục token đã thu hồi. Sau nâng cấp từ 0.3, cần đăng nhập lại vì token cũ chưa có claim phiên bản; mật khẩu hiện tại không thay đổi.

**Kiểm toán:** Ghi đăng nhập thành công/thất bại, tạo/cập nhật tài khoản, đặt lại/đổi mật khẩu, archive sản phẩm và điều chỉnh kho. Audit của thay đổi dữ liệu nằm trong cùng transaction: ghi audit lỗi thì nghiệp vụ rollback. Đăng nhập thất bại được commit trước khi trả 401 để vẫn có dấu vết. Retry điều chỉnh hoặc archive lặp không tạo thêm audit cho thay đổi đã hoàn tất. API nhật ký chỉ đọc.

**Theo dõi request:** Middleware gán UUID `X-Request-ID`, trả trong header và dùng chung trong lỗi, audit, JSON log. Log chỉ giữ trường cho phép như route mẫu, status và thời gian xử lý; không ghi body, mật khẩu, token hay query string. Access log thô của Uvicorn được tắt. Metadata audit cũng theo danh sách cho phép, không lưu nguyên payload.

### Cấu trúc và cách hiểu code

- `modules/users`: API/schema, truy vấn đọc và service quản trị tách riêng.
- `modules/audit`: ghi sự kiện theo whitelist, truy vấn phân trang và API chỉ đọc.
- `modules/auth`: kiểm tra token, đăng nhập và đổi mật khẩu cá nhân.
- `core/request_context.py`, `middleware.py`, `logging.py`: correlation ID và log có cấu trúc.
- `frontend/src/features/users`, `audit`, `auth`: màn hình, form và API theo tính năng; app chỉ điều phối.
- Migration `0003` thêm `users.auth_version` và bảng `audit_logs`, giữ nguyên dữ liệu hiện có.

Với .NET, JWT validation tương ứng JWT Bearer authentication, kiểm tra role tương ứng authorization policy; audit cùng transaction tương tự lưu entity và audit bằng cùng DbContext transaction. Request ID tương tự TraceIdentifier được truyền qua middleware. Đổi lại, mỗi request cần đọc user trong DB để quyền mới và thu hồi phiên có hiệu lực ngay; hiện chưa có refresh token.

### Chạy và nghiệm thu

```powershell
.\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini upgrade head
.\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini check
.\.venv\Scripts\python.exe -m ruff check backend
.\.venv\Scripts\python.exe -m ruff format --check backend
# Dùng TEST_DATABASE_URL trỏ DB test riêng như hướng dẫn Phase 2.
.\.venv\Scripts\python.exe -m pytest backend/tests -q
# Trong frontend:
npm run format:check
npm run lint
npm test
npm run build
```

Đã nghiệm thu 115 tests backend và 17 tests frontend, gồm thu hồi token, cạnh tranh Admin cuối, rollback khi ghi audit lỗi và bảo mật log. Biến `ADMIN_PASSWORD` trong `.env` dùng khi seed Admin ban đầu; đổi mật khẩu qua UI không tự sửa `.env`. Mật khẩu đăng nhập thực tế lấy từ DB.

Bước tiếp theo là Phase 4 AI Assistant; chưa tích hợp LLM trong Phase 3.
