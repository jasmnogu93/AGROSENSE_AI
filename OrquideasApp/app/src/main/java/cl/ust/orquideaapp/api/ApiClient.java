package cl.ust.orquideaapp.api;

import cl.ust.orquideaapp.config.ApiConfig;
import okhttp3.OkHttpClient;
import retrofit2.Retrofit;
import retrofit2.converter.gson.GsonConverterFactory;

import java.util.concurrent.TimeUnit;

/**
 * Cliente Singleton de Retrofit configurado con BASE_URL y conversor Gson.
 */
public class ApiClient {

    private static Retrofit retrofit = null;
    private static FieldApiService fieldApiService = null;

    public static synchronized FieldApiService getFieldApiService() {
        if (fieldApiService == null) {
            OkHttpClient okHttpClient = new OkHttpClient.Builder()
                    .connectTimeout(15, TimeUnit.SECONDS)
                    .readTimeout(15, TimeUnit.SECONDS)
                    .writeTimeout(15, TimeUnit.SECONDS)
                    .retryOnConnectionFailure(true)
                    .build();

            retrofit = new Retrofit.Builder()
                    .baseUrl(ApiConfig.BASE_URL)
                    .client(okHttpClient)
                    .addConverterFactory(GsonConverterFactory.create())
                    .build();

            fieldApiService = retrofit.create(FieldApiService.class);
        }
        return fieldApiService;
    }
}
