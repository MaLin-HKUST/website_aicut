# website_aicut

This iteration implements a minimal deployable slice:

- login page
- admin/user split
- admin can create companies, users, and material metadata
- normal users land on a welcome page
- web, api, and database run with Docker Compose

## Run

1. Copy `.env.example` to `.env`
2. Start services:

```bash
docker compose up --build
```

3. Open `http://localhost:3000/login`

Default admin account:

- username: `admin`
- password: value of `ADMIN_PASSWORD` in `.env`

## Services

- web: Next.js app on port `3000`
- api: FastAPI app on port `8000`
- db: PostgreSQL on port `5432`

