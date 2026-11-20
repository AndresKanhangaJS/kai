# syntax=docker/dockerfile:1

# Só para extrair o binário do Composer; a imagem final corre PHP 8.5 (ADR-0007/D-09),
# não o PHP embutido nesta imagem.
FROM composer:2 AS composer

FROM php:8.5-cli

RUN apt-get update && apt-get install -y --no-install-recommends \
        libzip-dev libonig-dev unzip git \
    && docker-php-ext-install pdo_mysql mbstring bcmath zip \
    && pecl install redis && docker-php-ext-enable redis \
    && rm -rf /var/lib/apt/lists/*

COPY --from=composer /usr/bin/composer /usr/local/bin/composer

WORKDIR /app
COPY . .
RUN composer install --no-interaction --prefer-dist --optimize-autoloader

COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh /app/artisan

ENTRYPOINT ["docker-entrypoint.sh"]
EXPOSE 8000
# Não usa "php artisan serve": esse comando filtra as variáveis de ambiente
# que reenvia para o processo que serve os pedidos (só as que já estão no
# ficheiro .env), por isso DB_HOST/DB_CONNECTION definidas só no Docker Compose
# nunca lá chegavam. Invoca o servidor embutido do PHP directamente, com o
# mesmo router que o Laravel usa, herdando o ambiente completo do contentor.
CMD ["php", "-S", "0.0.0.0:8000", "-t", "public", "vendor/laravel/framework/src/Illuminate/Foundation/resources/server.php"]
