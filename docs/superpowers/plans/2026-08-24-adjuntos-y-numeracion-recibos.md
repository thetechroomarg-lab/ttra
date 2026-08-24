# Adjuntos y Numeración de Recibos Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans task-by-task.

**Goal:** Adjuntar el PDF al email y emitir recibos correlativos desde `0001-1993`.

**Architecture:** Supabase asigna números con una secuencia y RPC atómica; FastAPI genera el PDF y lo entrega a Resend como adjunto base64. El pedido solo se marca emitido tras éxito.

**Spec:** `docs/superpowers/specs/2026-08-24-adjuntos-y-numeracion-recibos-design.md`

### Task 1: Numbering migration and tests
- [ ] Add a failing test asserting first number comes from `siguiente_numero_recibo` and email payload contains `recibo-0001-1993.pdf`.
- [ ] Add idempotent SQL sequence and `security definer` RPC returning `0001-<nextval>`.
- [ ] Extend the fake Supabase client with `rpc` for the receipt sequence.
- [ ] Run focused receipt tests.

### Task 2: Attach PDF on emission and resend
- [ ] Extend `enviar_email` with optional attachments and base64 encoding.
- [ ] Pass generated PDF attachment on first send and resend.
- [ ] Preserve number/date on resend and avoid persistence when email errors.
- [ ] Run full suite and `git diff --check`.
