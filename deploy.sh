#!/bin/bash
# Sweet Factory ERP - Deploy Script
set -e

echo "🚀 Sweet Factory ERP - Deploy boshlandi"

# .env tekshirish
if [ ! -f .env ]; then
    echo "❌ .env fayl topilmadi!"
    echo "   cp .env.example .env  →  ichini to'ldiring"
    exit 1
fi

# Build va ishga tushirish
echo "📦 Docker image lar yasalyapti..."
docker compose build --no-cache

echo "🗄️  Database ishga tushirilmoqda..."
docker compose up -d db
sleep 5

echo "⚙️  Migration ishga tushirilmoqda..."
docker compose run --rm backend alembic upgrade head

echo "🌱 Seed data yuklanmoqda..."
docker compose run --rm backend python seed_data.py

echo "🎯 Barcha servislar ishga tushirilmoqda..."
docker compose up -d

echo ""
echo "✅ Deploy tugadi!"
echo "   Dashboard:  http://$(hostname -I | awk '{print $1}')"
echo "   API Docs:   http://$(hostname -I | awk '{print $1}')/docs"
echo ""
echo "   Login: admin / Admin@123!"
