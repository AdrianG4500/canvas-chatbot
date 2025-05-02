from openai_utils.uploader import limpiar_vector_stores

VECTOR_STORE_ID_A_CONSERVAR = "vs_67efafcb3f988191a08a2c7e07ee73e7"

if __name__ == "__main__":
    limpiar_vector_stores(VECTOR_STORE_ID_A_CONSERVAR)