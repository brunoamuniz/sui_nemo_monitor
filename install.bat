@echo off
echo ========================================
echo    SUI MONITOR - INSTALACAO
echo ========================================
echo.

REM Verifica se Python está instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo ERRO: Python nao encontrado!
    echo.
    echo Por favor, instale o Python 3.8+ primeiro:
    echo 1. Acesse: https://www.python.org/downloads/
    echo 2. Baixe a versao mais recente
    echo 3. Execute o instalador
    echo 4. MARQUE a opcao "Add Python to PATH"
    echo 5. Execute este script novamente
    echo.
    pause
    exit /b 1
)

echo Python encontrado!
python --version
echo.

REM Cria ambiente virtual se não existir
if not exist "venv" (
    echo Criando ambiente virtual Python...
    python -m venv venv
    if errorlevel 1 (
        echo ERRO: Falha ao criar ambiente virtual!
        pause
        exit /b 1
    )
    echo Ambiente virtual criado com sucesso!
) else (
    echo Ambiente virtual ja existe!
)

REM Ativa o ambiente virtual
echo Ativando ambiente virtual...
call venv\Scripts\activate.bat

REM Instala dependências no ambiente virtual
echo Instalando dependencias no ambiente virtual...
pip install -r requirements.txt

if errorlevel 1 (
    echo ERRO: Falha ao instalar dependencias!
    pause
    exit /b 1
)

echo.
echo Dependencias instaladas com sucesso!
echo.

REM Cria diretório de cache
if not exist "cache" mkdir cache
echo Diretorio de cache criado!

REM Verifica se .env existe
if not exist ".env" (
    echo.
    echo ATENCAO: Arquivo .env nao encontrado!
    echo.
    echo Por favor, configure o arquivo .env com:
    echo - Sua API do Telegram (TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_PHONE, TELEGRAM_CHAT_ID)
    echo - Configuracoes dos protocolos (NEMO_PACKAGE_ID, SCALLOP_PACKAGE_ID, etc.)
    echo - Configuracoes de monitoramento (CHECK_INTERVAL_MINUTES, etc.)
    echo.
    echo Copie o arquivo .env.example para .env e edite:
    echo   copy .env.example .env
    echo.
    echo Veja o README.md para mais detalhes sobre as configuracoes.
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================
echo    INSTALACAO CONCLUIDA COM SUCESSO!
echo ========================================
echo.
echo Para iniciar o monitoramento, execute:
echo   startup.bat
echo.
echo Ou manualmente:
echo   python main.py --continuous
echo.
pause
