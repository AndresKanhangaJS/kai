<?php

use Tests\TestCase;

/*
 * Pest (M02 E2.1, .claude/rules/laravel.md). Os testes existentes são classes
 * PHPUnit (`Tests\TestCase`) e correm tal como estão; os testes novos podem
 * usar a sintaxe do Pest. Os testes de Feature em ficheiros Pest usam o
 * TestCase do Laravel.
 */

pest()->extend(TestCase::class)->in('Feature');
