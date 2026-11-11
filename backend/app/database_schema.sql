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

-- =============================================================================
-- INSERCIÓN DE DATOS INICIALES (SEED DATA)
-- =============================================================================

INSERT OR IGNORE INTO modulos_hidroponicos (id, nombre, descripcion, broker_topic_telemetria, broker_topic_comandos)
VALUES (
    'celda-01', 
    'Bandeja Piloto 01', 
    'Prototipo hidropónico NFT de 1 nivel con ESP32, BME280, DHT11, Relé 5V, Servo SG90 y PaP ULN2003',
    'agrosense/telemetria/celda01',
    'agrosense/comandos/celda01'
);

INSERT OR IGNORE INTO perfiles_cultivo (especie, temp_min, temp_max, humedad_min, humedad_max, dpv_min_kpa, dpv_max_kpa, recirculacion_minutos, intervalo_riego_horas)
VALUES ('Frutilla Hidropónica', 18.0, 24.0, 55.0, 75.0, 0.8, 1.2, 15, 2);

INSERT OR IGNORE INTO asignacion_cultivo_modulo (modulo_id, perfil_id, estado_cultivo)
VALUES ('celda-01', 1, 'FLORACION');
