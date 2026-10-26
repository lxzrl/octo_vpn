# Запуск бота на своём компьютере (Windows) для теста: без Docker, Postgres и Redis.
# Запускается двойным щелчком по start-local.bat. Данные хранятся в файле octo.db рядом.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Ask($prompt, $pattern, $hint) {
    while ($true) {
        $answer = (Read-Host $prompt).Trim()
        if ($answer -match $pattern) { return $answer }
        Write-Host "  $hint" -ForegroundColor Yellow
    }
}

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "Ставлю uv (менеджер Python)..."
    powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex"
    $env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
}

$configure = -not (Test-Path .env)
if (-not $configure) {
    $again = Read-Host "Бот уже настроен. Ввести токен, ID и ссылку заново? [y/N]"
    $configure = $again -match '^[YyДд]'
}

if ($configure) {
    Write-Host ""
    Write-Host "1. Токен бота от @BotFather"
    $token = Ask "Токен бота от @BotFather" '^[0-9]+:[A-Za-z0-9_-]{30,}$' "Не похоже на токен. Он выглядит так: 123456789:AAH..."
    Write-Host ""
    Write-Host "2. Ваш Telegram ID (узнать: @userinfobot), вы будете админом бота"
    $adminId = Ask "Ваш Telegram ID" '^[0-9]{5,15}$' "Нужно число, например 123456789"
    Write-Host ""
    Write-Host "3. VLESS-ссылка: её бот будет выдавать пользователям как ключ"
    $vless = Ask "VLESS-ссылка" "^vless://[^']+$" "Ссылка должна начинаться с vless://"

    $lines = @(
        "# Локальный запуск (start-local.bat)",
        "BOT_TOKEN='$token'",
        "ADMIN_IDS=$adminId",
        "DATABASE_URL=sqlite+aiosqlite:///octo.db",
        "REDIS_URL=",
        "VPN_PANEL=demo",
        "DEMO_SUBSCRIPTION_URL='$vless'",
        "# Если Telegram без VPN не открывается: socks5://127.0.0.1:порт из настроек вашего VPN-клиента",
        "TELEGRAM_PROXY="
    )
    [IO.File]::WriteAllLines((Join-Path $PSScriptRoot ".env"), $lines, (New-Object Text.UTF8Encoding $false))
}

Write-Host ""
Write-Host "Ставлю зависимости и проверяю (первый раз 1-2 минуты)..."
uv run --no-dev python -m app.check
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Проверка нашла проблемы (строки с X выше). Если нет связи с Telegram - включите VPN на компьютере." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Бот запущен. Напишите ему /start в Telegram, админка - /admin. Остановить - закройте это окно или Ctrl+C." -ForegroundColor Green
uv run --no-dev python -m app
