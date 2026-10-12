# CommerceIQ-AI

## Run with Docker

1. Start the app from this project root:
   ```bash
   docker compose up --build
   ```
   Compose starts PostgreSQL and the backend/frontend services. The bundled database
   credentials and local image storage are for local development only.
2. Open the app in your browser:
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:8000/docs
3. To reset the database and container state:
   ```bash
   docker compose down -v
   ```

If this project was downloaded into a same-named folder, this directory (the one containing this
README) is the project root. Run the setup commands below from this directory, not from its parent.
The backend container listens on the cloud platform's `PORT` environment variable and defaults
to port `8000` for local Docker use.

## Hosted persistence (Supabase)

For a persistent cloud deployment, create a Supabase project and configure these variables
in the backend service's hosting dashboard (do not commit secrets or add them to the frontend):

- `DATABASE_URL`: Supabase's PostgreSQL connection string from **Project Settings → Database**.
  Use the session pooler connection if the host cannot use IPv6, URL-encode special characters
  in the database password, and require SSL (`sslmode=require`).
- `IMAGE_STORAGE_BACKEND=supabase`
- `SUPABASE_URL`: the project URL from **Project Settings → API**.
- `SUPABASE_SERVICE_ROLE_KEY`: the server-only service-role key from **Project Settings → API**.
  Never expose this key in frontend variables or client code.
- `SUPABASE_STORAGE_BUCKET=product-images` (or the name of your bucket).

Create a **public** Storage bucket with that name in Supabase before enabling image uploads.
The SQL in [`supabase/storage.sql`](./supabase/storage.sql) creates it with the 5 MB limit and
image MIME types accepted by the API. Run it in the Supabase SQL Editor. The backend uploads
product images to that bucket and saves their public URLs in PostgreSQL.
If the storage backend is selected but its credentials or bucket are missing, uploads return an
explicit configuration error rather than silently using ephemeral container storage. Local
development defaults to SQLite and local `backend/uploads` files.

To configure Render, connect this repository and use the included [`render.yaml`](./render.yaml)
Blueprint. Enter the Supabase connection string, project URL, service-role key, Firebase project ID,
and frontend origins when prompted. `SEED_DATA_ON_EMPTY=false` prevents application startup from
running the development CSV loader, which drops and recreates tables when it seeds an empty database.
For an initially empty hosted catalog, run the CSV loader once as a controlled deployment job only
after reviewing its destructive behavior, or add catalog data through a dedicated import workflow.

## Folder layout (yes, frontend + backend go in ONE folder)

```
CommerceIQ-AI/
├── .gitignore
├── README.md
├── backend/
│   ├── main.py  models.py  database.py  requirements.txt  .env.example
│   ├── data.csv                <-- copy your 1000-product CSV here
│   ├── scripts/load_data.py
│   └── src/recommendation/recommender.py  (+ __init__.py files)
└── frontend/
    ├── package.json, index.html, vite.config.ts ...   <-- your existing Vite files
    ├── .env.example
    └── src/  App.tsx  api.ts  firebase.ts  main.tsx  *.css  vite-env.d.ts
```
Copy the files from this download over your existing ones (keep your own
`package.json`, `index.html`, `vite.config.ts`, `tsconfig*.json`, `node_modules`).
One repo, one `git push`. Don't commit `.venv`, `node_modules`, `*.db`, `.env`
(the .gitignore already excludes them).

## Run it

**Backend** (terminal 1)
```
cd backend
copy .env.example .env
python -m venv .venv
.venv\Scripts\activate            # Windows   (Mac/Linux: source .venv/bin/activate)
pip install -r requirements.txt
python scripts/load_data.py       # builds ecommerce.db from data.csv (run once; re-run wipes + reloads)
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Frontend** (terminal 2)
```
cd frontend
copy .env.example .env            # Mac/Linux: cp .env.example .env
npm install
npm run dev
```
Open the URL Vite prints (usually http://localhost:5173).
The frontend defaults to `http://127.0.0.1:8000`, matching the backend command above.
For seller product management, sign in with a seller account; adding, editing, deleting, and
listing products call the authenticated `/seller/products` API. The backend `.env` must use the
same `FIREBASE_PROJECT_ID` as the Firebase project configured by the frontend.

## How to test

1. **Backend health** – open http://127.0.0.1:8000/docs (Swagger). Expect:
   - `GET /products` -> 1000 items, `GET /categories` -> 28
   - `GET /products/3/market-insight` -> `BUY_NOW`, discount about -32%, 5 competitors
   - `GET /products/1/recommendations` -> 5 similar products
   - `GET /analytics/overview` -> totals, category breakdown, top discounts, trending
   - `GET /analytics/buyer` -> best_deals, wait_list, top_rated, trending
   - `GET /analytics/seller` (and `?category_id=2`) -> kpis, pricing_opportunities, margin_pressure, competition
2. **Frontend** – with backend running:
   - Products page: real products/images, category chips (28 real categories) filter correctly
   - Click a product: Market Insight (buy/wait badge, list vs current price, loss %, competitors),
     reviews, and "You may also like"
   - Click a competitor row: jumps to that product
   - **Gates:** logged out -> click Buyer/Seller Dashboard -> "Please log in". After login, first visit asks
     "Buyer or Seller?". A buyer opening the Seller Dashboard sees "Sellers only" + a switch button (and vice versa).
   - **Buyer Dashboard:** best deals, wait list, top rated, trending (click a row to open the product)
   - **Checkout:** add products to the cart, continue to checkout, enter delivery details, review the order,
     and place it as a pending order. Online payment is not configured.
   - **Seller Dashboard:** add, edit, delete, and upload images for your listings; category picker,
     KPIs, pricing opportunities, margin pressure, crowded categories, and store-wide overview
     (analytics auto-refresh every 30s)
3. **Two laptops on the same Wi-Fi** – on the backend machine find its IP (`ipconfig`),
   then on the frontend machine set `VITE_API_BASE_URL=http://<that-ip>:8000` in `frontend/.env`
   and restart `npm run dev`. On the backend machine set
   `FRONTEND_ORIGINS=http://<frontend-ip>:5173` in `backend/.env` (allow port 8000 in the firewall).

## Notes
- "Real-time" = computed fresh from the database on every request (Insights page re-polls every 30s).
  There is no live Amazon feed; the data is the static scraped CSV.
- Buy/Wait is a transparent rule on discount depth (>=25% off BUY NOW, 10-25% GOOD DEAL, small/none WAIT,
  price above list PRICE RISING, no list price NO_DATA). It is a heuristic, not a forecast.
- "Profit/loss %" = current price vs original list price. True seller profit needs cost data, which isn't in the CSV.
- Competitors = products in the same category closest in price.
- **Rupees:** the CSV is mostly USD, so `load_data.py` converts to INR while loading (default 88 per USD, 115 per GBP).
  Change with `USD_TO_INR=90 python scripts/load_data.py`. Re-run the script after changing the rate.
- Dashboard visibility is controlled in the UI, and seller product APIs additionally verify the Firebase ID
  token and seller role on the backend. Analytics should not be treated as seller-owned inventory or profit data.
- The seller dashboard summarizes the signed-in seller's own listings and compares their prices with category market
  medians. Imported CSV products do not belong to a signed-in seller; new listings are assigned to that seller.
  Demand signals for manually created listings remain unavailable unless purchase data is added.
