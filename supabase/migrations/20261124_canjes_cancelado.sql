-- Plan Canje: el admin puede cancelar una solicitud pendiente (además de
-- aprobarla o rechazarla). El motivo opcional queda en motivo_rechazo.
alter table canjes drop constraint if exists canjes_estado_check;
alter table canjes add constraint canjes_estado_check
  check (estado in ('pendiente', 'aprobado', 'rechazado', 'cancelado'));
