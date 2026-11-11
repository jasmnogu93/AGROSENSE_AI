-- =============================================================================
-- ESQUEMA DE BASE DE DATOS RELACIONAL: AGROSENSE AI (ASAI)
-- COMPATIBLE CON SQLITE Y POSTGRESQL / AZURE DATABASE
-- MODELO CELULAR PARA BANDEJA HIDROPÓNICA PILOTO 01 (HARDWARE MVP REAL)
-- =============================================================================

-- 1. Tabla de Módulos Físicos
CREATE TABLE IF NOT EXISTS modulos_hidroponicos (
    id VARCHAR(50) PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    descripcion TEXT,
    ubicacion_fisica VARCHAR(100) DEFAULT 'Santo Tomás Temuco - Lab IoT',
    broker_topic_telemetria VARCHAR(100) NOT NULL,
    broker_topic_comandos VARCHAR(100) NOT NULL,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    activo BOOLEAN DEFAULT 1
);

-- 2. Tabla de Perfiles de Especies Cultivadas
CREATE TABLE IF NOT EXISTS perfiles_cultivo (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    especie VARCHAR(100) NOT NULL,
    temp_min REAL NOT NULL DEFAULT 18.0,
    temp_max REAL NOT NULL DEFAULT 24.0,
    humedad_min REAL NOT NULL DEFAULT 55.0,
    humedad_max REAL NOT NULL DEFAULT 75.0,
    dpv_min_kpa REAL NOT NULL DEFAULT 0.8,
    dpv_max_kpa REAL NOT NULL DEFAULT 1.2,
    recirculacion_minutos INTEGER DEFAULT 15,
    intervalo_riego_horas INTEGER DEFAULT 2
);

-- 3. Tabla de Asociación Módulo - Cultivo
CREATE TABLE IF NOT EXISTS asignacion_cultivo_modulo (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    modulo_id VARCHAR(50) NOT NULL,
    perfil_id INTEGER NOT NULL,
    fecha_siembra DATE DEFAULT CURRENT_DATE,
    estado_cultivo VARCHAR(50) DEFAULT 'FLORACION',
    FOREIGN KEY (modulo_id) REFERENCES modulos_hidroponicos(id),
    FOREIGN KEY (perfil_id) REFERENCES perfiles_cultivo(id)
);

-- 4. Tabla de Telemetría Histórica (Series Temporales del Hardware Real)
CREATE TABLE IF NOT EXISTS telemetria_historica (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    modulo_id VARCHAR(50) NOT NULL,
    fecha_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Variables Físicas Reales MVP
    temp_ambiente REAL NOT NULL,              -- DHT11 / BME280
    humedad_ambiente REAL NOT NULL,           -- DHT11
    presion_atmosferica REAL NOT NULL,        -- BME280 / BMP280 (hPa)
    dpv_kpa REAL,                             -- Déficit Presión de Vapor calculado
    nivel_estanque REAL NOT NULL,             -- Sensor Resistivo GPIO 34/25 (%)
    
    -- Estado de Actuadores Físicos en el Instante de Lectura
    bomba_encendida BOOLEAN DEFAULT 0,        -- Relé 5V (GPIO 26)
    servo_angulo INTEGER DEFAULT 0,           -- SG90 PWM (GPIO 18, 0° a 180°)
    pasos_motor_acumulados INTEGER DEFAULT 0, -- ULN2003 28BYJ-48
    
    -- Extensiones Futuras (NULLABLE - Se activan solo al conectar sondas)
    ph_solucion REAL,                         -- Sonda pH análoga (Fase 2)
    conductividad_ec REAL,                    -- Sonda EC (Fase 2)
    luz_lux REAL,                             -- Fotocelda LDR (Fase 2)
    
    origen_dato VARCHAR(20) DEFAULT 'MQTT_ESP32',
    FOREIGN KEY (modulo_id) REFERENCES modulos_hidroponicos(id)
);

-- 5. Tabla Polimórfica de Comandos a Actuadores (Soporta N Actuadores)
CREATE TABLE IF NOT EXISTS registro_comandos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    modulo_id VARCHAR(50) NOT NULL,
    actuador VARCHAR(50) NOT NULL,             -- 'bomba_agua', 'servo_ventilacion', 'motor_nutrientes'
    accion VARCHAR(50) NOT NULL,               -- 'ON', 'OFF', 'SET_ANGLE', 'DISPENSE_STEPS'
    parametro_valor REAL DEFAULT 0.0,          -- 90 (grados), 512 (pasos), 60 (segundos)
    disparado_por VARCHAR(50) NOT NULL,        -- 'ANDROID_APP', 'WEB_DASHBOARD', 'JEV_RULE'
    fecha_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (modulo_id) REFERENCES modulos_hidroponicos(id)
);

-- 6. Tabla de Alertas y Eventos Críticos
CREATE TABLE IF NOT EXISTS alertas_sistema (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    modulo_id VARCHAR(50) NOT NULL,
    severidad VARCHAR(20) NOT NULL,            -- 'INFO', 'WARNING', 'CRITICAL'
    mensaje TEXT NOT NULL,
    leida BOOLEAN DEFAULT 0,
    fecha_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (modulo_id) REFERENCES modulos_hidroponicos(id)
);

-- 7. Tabla de Calendario Semanal de Riego (RF1 Integración II & Recirculación)
CREATE TABLE IF NOT EXISTS calendario_semanal (
    modulo_id VARCHAR(50) PRIMARY KEY,
    dias_activos_json TEXT NOT NULL,           -- JSON list: ["Lun", "Mié", "Vie"]
    hora_riego VARCHAR(10) NOT NULL DEFAULT '08:30',
    duracion_minutos INTEGER NOT NULL DEFAULT 20,
    intervalo_horas INTEGER NOT NULL DEFAULT 2,
    actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (modulo_id) REFERENCES modulos_hidroponicos(id)
);

-- 8. Tabla de Estado Operativo Persistente por Módulo (Evita pérdida en RAM)
CREATE TABLE IF NOT EXISTS estado_modulo (
    modulo_id VARCHAR(50) PRIMARY KEY,
    temp_ambiente REAL NOT NULL,
    humedad_ambiente REAL NOT NULL,
    presion_hpa REAL NOT NULL DEFAULT 1013.25,
    nivel_estanque REAL NOT NULL DEFAULT 85.0,
    dpv_kpa REAL,
    bomba_encendida BOOLEAN DEFAULT 0,
    servo_angulo INTEGER DEFAULT 0,
    pasos_motor_acumulados INTEGER DEFAULT 0,
    humedad_sustrato REAL,
    actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (modulo_id) REFERENCES modulos_hidroponicos(id)
);

-- =============================================================================
-- INSERCIÓN DE DATOS INICIALES (SEED DATA IDEMPOTENTE)
-- =============================================================================

INSERT OR IGNORE INTO modulos_hidroponicos (id, nombre, descripcion, broker_topic_telemetria, broker_topic_comandos)
VALUES (
    'celda-01', 
    'Mini Torre Domiciliaria ASAI (Celda 01)', 
    'Prototipo hidropónico NFT de 1 nivel con ESP32, BME280, DHT11, Relé 5V, Servo SG90 y PaP ULN2003',
    'agrosense/telemetria/celda01',
    'agrosense/comandos/celda01'
);

INSERT OR IGNORE INTO modulos_hidroponicos (id, nombre, descripcion, broker_topic_telemetria, broker_topic_comandos)
VALUES (
    'invernadero-orquideas',
    'Invernadero Orquídeas (Caso IEI-094)',
    'Cultivo tradicional en invernadero con calendario semanal (80% HR y 18-24 °C)',
    'agrosense/telemetria/orquideas01',
    'agrosense/comandos/orquideas01'
);

INSERT INTO perfiles_cultivo (especie, temp_min, temp_max, humedad_min, humedad_max, dpv_min_kpa, dpv_max_kpa, recirculacion_minutos, intervalo_riego_horas)
SELECT 'Frutilla Hidropónica', 18.0, 24.0, 55.0, 75.0, 0.8, 1.2, 15, 2
WHERE NOT EXISTS (SELECT 1 FROM perfiles_cultivo WHERE especie = 'Frutilla Hidropónica');

INSERT INTO perfiles_cultivo (especie, temp_min, temp_max, humedad_min, humedad_max, dpv_min_kpa, dpv_max_kpa, recirculacion_minutos, intervalo_riego_horas)
SELECT 'Orquídeas de Invernadero (Phalaenopsis)', 18.0, 24.0, 75.0, 85.0, 0.5, 0.9, 20, 24
WHERE NOT EXISTS (SELECT 1 FROM perfiles_cultivo WHERE especie = 'Orquídeas de Invernadero (Phalaenopsis)');

INSERT INTO asignacion_cultivo_modulo (modulo_id, perfil_id, estado_cultivo)
SELECT 'celda-01', 1, 'FLORACION'
WHERE NOT EXISTS (SELECT 1 FROM asignacion_cultivo_modulo WHERE modulo_id = 'celda-01');

INSERT OR IGNORE INTO calendario_semanal (modulo_id, dias_activos_json, hora_riego, duracion_minutos, intervalo_horas)
VALUES ('invernadero-orquideas', '["Lun", "Mié", "Vie"]', '08:30', 20, 24);

INSERT OR IGNORE INTO calendario_semanal (modulo_id, dias_activos_json, hora_riego, duracion_minutos, intervalo_horas)
VALUES ('celda-01', '["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]', '08:00', 15, 2);

INSERT OR IGNORE INTO estado_modulo (modulo_id, temp_ambiente, humedad_ambiente, presion_hpa, nivel_estanque, dpv_kpa, bomba_encendida, servo_angulo, pasos_motor_acumulados)
VALUES ('celda-01', 21.8, 62.4, 1014.5, 85.0, 0.98, 0, 0, 0);

INSERT OR IGNORE INTO estado_modulo (modulo_id, temp_ambiente, humedad_ambiente, presion_hpa, nivel_estanque, dpv_kpa, bomba_encendida, servo_angulo, pasos_motor_acumulados, humedad_sustrato)
VALUES ('invernadero-orquideas', 21.4, 79.8, 1013.8, 90.0, 0.51, 0, 0, 0, 68.0);
