# Realtor Leads Webhook

Простой webhook для приёма лидов и отправки в Pipedrive, WhatsApp (Twilio), Google Sheets и email.

## Быстрый старт
1. Скопируйте `.env.example` в `.env` и заполните значения.
2. (Опционально) положите JSON с Google service account в `service-account.json` и укажите путь в `.env`.
3. Установите зависимости и запустите сервер:

```bash
npm install
npm run dev    # используется nodemon
```

4. Тестируйте endpoint:

```bash
curl -X POST http://localhost:3000/lead \
  -H "Content-Type: application/json" \
  -d '{"name":"Иван Петров","phone":"+79991234567","email":"ivan@example.com","source":"Instagram","property":"3-комнатная","message":"срочно"}'
```

## Примечания
- Если вы не указываете реальные ключи, сервер будет запускаться, но интеграции с Pipedrive/Twilio/Sheets не будут работать.
- За безопасность: храните `.env` и `service-account.json` вне публичного репозитория.

## Что я могу сделать дальше
- Помочь заполнить `.env` и протестировать интеграции (нужны ключи).
- Настроить ngrok / публичный URL для приёма лидов от Facebook/Instagram.
