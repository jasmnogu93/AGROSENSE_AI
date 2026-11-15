package cl.ust.orquideaapp.config;

/**
 * Configuración centralizada de red para AgroFieldService (Invernadero de Orquídeas).
 * 10.0.2.2 mapea a localhost (127.0.0.1) del equipo host desde el emulador de Android.
 */
public class ApiConfig {
    public static final String BASE_URL = "http://10.0.2.2:8000/api/v1/services/field/";

    // Funciono pero tuve que cambiar El url a mi direccion wifi real pero por el momento le dejo este
}
