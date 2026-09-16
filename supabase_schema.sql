-- ========================================================
-- SCRIPT DE INICIALIZACIÓN DE BASE DE DATOS PARA SUPABASE
-- Sistema de Gestión de Inventario y Ventas
-- ========================================================

-- 1. Tabla Clientes
CREATE TABLE IF NOT EXISTS clientes (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(255) NOT NULL,
    cedula VARCHAR(50),
    telefono VARCHAR(50),
    email VARCHAR(255),
    direccion TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. Tabla Productos
CREATE TABLE IF NOT EXISTS productos (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(100) UNIQUE,
    nombre VARCHAR(255) NOT NULL,
    descripcion TEXT,
    categoria VARCHAR(100),
    precio_usd NUMERIC(12, 2) NOT NULL DEFAULT 0,
    costo_usd NUMERIC(12, 2) NOT NULL DEFAULT 0,
    stock INT NOT NULL DEFAULT 0,
    stock_minimo INT DEFAULT 5,
    activo INT DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. Tabla Ventas
CREATE TABLE IF NOT EXISTS ventas (
    id SERIAL PRIMARY KEY,
    cliente_id INT REFERENCES clientes(id) ON DELETE SET NULL,
    total_usd NUMERIC(12, 2) NOT NULL DEFAULT 0,
    total_bs NUMERIC(12, 2) NOT NULL DEFAULT 0,
    subtotal_usd NUMERIC(12, 2) NOT NULL DEFAULT 0,
    iva_usd NUMERIC(12, 2) NOT NULL DEFAULT 0,
    subtotal_bs NUMERIC(12, 2) NOT NULL DEFAULT 0,
    iva_bs NUMERIC(12, 2) NOT NULL DEFAULT 0,
    tasa_cambio NUMERIC(12, 2) NOT NULL DEFAULT 1,
    notas TEXT,
    fecha TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    cerrada INT DEFAULT 0
);

-- 4. Tabla Detalle de Ventas
CREATE TABLE IF NOT EXISTS venta_detalles (
    id SERIAL PRIMARY KEY,
    venta_id INT NOT NULL REFERENCES ventas(id) ON DELETE CASCADE,
    producto_id INT NOT NULL REFERENCES productos(id),
    cantidad INT NOT NULL,
    precio_unitario_usd NUMERIC(12, 2) NOT NULL,
    subtotal_usd NUMERIC(12, 2) NOT NULL
);

-- 5. Tabla Pagos de Ventas (Soporte tradicional y Cashea)
CREATE TABLE IF NOT EXISTS venta_pagos (
    id SERIAL PRIMARY KEY,
    venta_id INT NOT NULL REFERENCES ventas(id) ON DELETE CASCADE,
    metodo_pago VARCHAR(50) NOT NULL,
    monto_usd NUMERIC(12, 2) NOT NULL DEFAULT 0,
    monto_bs NUMERIC(12, 2) NOT NULL DEFAULT 0
);

-- 6. Tabla Compras
CREATE TABLE IF NOT EXISTS compras (
    id SERIAL PRIMARY KEY,
    proveedor VARCHAR(255),
    total_usd NUMERIC(12, 2) NOT NULL DEFAULT 0,
    notas TEXT,
    fecha TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 7. Tabla Detalle de Compras
CREATE TABLE IF NOT EXISTS compra_detalles (
    id SERIAL PRIMARY KEY,
    compra_id INT NOT NULL REFERENCES compras(id) ON DELETE CASCADE,
    producto_id INT NOT NULL REFERENCES productos(id),
    cantidad INT NOT NULL,
    precio_unitario_usd NUMERIC(12, 2) NOT NULL,
    subtotal_usd NUMERIC(12, 2) NOT NULL
);

-- 8. Tabla Cierres Diarios
CREATE TABLE IF NOT EXISTS cierres_diarios (
    id SERIAL PRIMARY KEY,
    fecha DATE NOT NULL UNIQUE,
    total_ventas_usd NUMERIC(12, 2) DEFAULT 0,
    total_ventas_bs NUMERIC(12, 2) DEFAULT 0,
    total_efectivo_usd NUMERIC(12, 2) DEFAULT 0,
    total_pago_movil_bs NUMERIC(12, 2) DEFAULT 0,
    total_punto_bs NUMERIC(12, 2) DEFAULT 0,
    total_divisas_usd NUMERIC(12, 2) DEFAULT 0,
    num_ventas INT DEFAULT 0,
    notas TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 9. Tabla Configuración
CREATE TABLE IF NOT EXISTS configuracion (
    clave VARCHAR(100) PRIMARY KEY,
    valor TEXT NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO configuracion (clave, valor) VALUES ('tasa_cambio', '36.50') ON CONFLICT (clave) DO NOTHING;
INSERT INTO configuracion (clave, valor) VALUES ('nombre_negocio', 'Mi Negocio') ON CONFLICT (clave) DO NOTHING;

-- 10. Tabla Movimientos / Auditoría
CREATE TABLE IF NOT EXISTS movimientos (
    id SERIAL PRIMARY KEY,
    entidad VARCHAR(50) NOT NULL,
    entidad_id INT NOT NULL,
    accion VARCHAR(50) NOT NULL,
    descripcion TEXT NOT NULL,
    datos_anteriores TEXT,
    datos_nuevos TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Índices recomendados para optimización de consultas
CREATE INDEX IF NOT EXISTS idx_productos_activo_codigo ON productos(activo, codigo);
CREATE INDEX IF NOT EXISTS idx_ventas_fecha ON ventas(fecha);
CREATE INDEX IF NOT EXISTS idx_venta_detalles_venta ON venta_detalles(venta_id);
CREATE INDEX IF NOT EXISTS idx_venta_pagos_venta ON venta_pagos(venta_id);
