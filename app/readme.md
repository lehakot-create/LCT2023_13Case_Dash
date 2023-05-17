# Качаем демобазу 
https://www.postgrespro.ru/education/demodb

любой архив demo-***.zip

например demo-small-20170815.zip

Распаковываем и кладем рядом с Dockerfile

В консоли фигачим:

docker-compose up (поднимаем контейнер)


docker ps (копируем CONTAINER_ID)

docker cp demo-small-20170815.sql CONTAINER_ID:/  (копируем файл в контейнер)


docker exec -it CONTAINER_ID sh   (заходим внутрь контейнера)


ls  (в выводе должен быть скопированный файл demo-small-***.sql)


psql -f demo-small-20170815.sql db_name alex  (создает демобазу)


ctrl+d  (выходим из контейнера)
