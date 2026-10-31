"""
Prueba del flujo completo del ciclo de vida de un ticket:
Registrado → Clasificado → Asignado → En atención → Resuelto → Cerrado
"""
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from apps.catalogos.models import Categoria, ServicioAfectado, SLA
from apps.tickets.models import Ticket, BitacoraTicket
from apps.tickets.state_machine import TicketStateMachine

# Obtener usuarios
solicitante = User.objects.get(username='solicitante1')
operador = User.objects.get(username='operador1')
tecnico = User.objects.get(username='tecnico1')

# Obtener catálogos
categoria = Categoria.objects.get(nombre='Aplicación')
servicio = ServicioAfectado.objects.filter(categoria=categoria).first()

print('=== PRUEBA DEL FLUJO COMPLETO DE TICKET ===')
print()

# 1. Crear ticket (estado: Registrado)
ticket = Ticket.objects.create(
    descripcion='El sistema ERP no permite acceder al módulo de facturación. '
                'Al intentar ingresar aparece el error "Error de conexión a la base de datos". '
                'Esto está afectando a todo el equipo de contabilidad.',
    servicio_afectado=servicio,
    categoria=categoria,
    solicitante=solicitante,
    estado=Ticket.ESTADO_REGISTRADO,
)
BitacoraTicket.objects.create(
    ticket=ticket,
    usuario=solicitante,
    accion='Registro de incidencia',
    detalle='Ticket de prueba registrado por solicitante1',
    valor_anterior='',
    valor_nuevo=Ticket.ESTADO_REGISTRADO,
)
print(f'1. Ticket creado: {ticket.codigo} | Estado: {ticket.estado}')
assert ticket.estado == Ticket.ESTADO_REGISTRADO

# 2. Clasificar (operador)
sm = TicketStateMachine(ticket, operador)
sm.clasificar(
    categoria=categoria,
    servicio_afectado=servicio,
    prioridad_operador=Ticket.PRIORIDAD_ALTA,
)
ticket.refresh_from_db()
print(f'2. Clasificado: prioridad={ticket.prioridad_operador} | SLA={ticket.sla_maximo_horas}h | Estado={ticket.estado}')
assert ticket.estado == Ticket.ESTADO_CLASIFICADO
assert ticket.prioridad_operador == 'Alta'
assert ticket.sla_maximo_horas == 4  # Alta=4h según SLA

# 3. Asignar técnico (operador)
sm = TicketStateMachine(ticket, operador)
sm.asignar(tecnico=tecnico)
ticket.refresh_from_db()
print(f'3. Asignado a: {ticket.tecnico_asignado.username} | Estado: {ticket.estado}')
assert ticket.estado == Ticket.ESTADO_ASIGNADO
assert ticket.tecnico_asignado == tecnico

# 4. Tomar ticket (técnico — estampa TPA)
sm = TicketStateMachine(ticket, tecnico)
sm.tomar()
ticket.refresh_from_db()
print(f'4. Tomado: TPA estampado={ticket.fecha_hora_primera_atencion} | Estado={ticket.estado}')
assert ticket.estado == Ticket.ESTADO_EN_ATENCION
assert ticket.fecha_hora_primera_atencion is not None

# 5. Resolver con solución
sm = TicketStateMachine(ticket, tecnico)
sm.resolver(solucion_aplicada='Se reinició el servicio de conexión a la base de datos del ERP. '
                              'Se verificó que el archivo de configuración tenía una contraseña expirada. '
                              'Se actualizó la contraseña y se probó el acceso exitosamente.')
ticket.refresh_from_db()
print(f'5. Resuelto: dentro_sla={ticket.dentro_sla} | cierre={ticket.fecha_hora_cierre} | Estado={ticket.estado}')
assert ticket.estado == Ticket.ESTADO_RESUELTO
assert ticket.solucion_aplicada is not None
assert ticket.fecha_hora_cierre is not None
assert ticket.dentro_sla is not None

# 6. Cerrar (operador)
sm = TicketStateMachine(ticket, operador)
sm.cerrar()
ticket.refresh_from_db()
print(f'6. Cerrado: Estado={ticket.estado}')
assert ticket.estado == Ticket.ESTADO_CERRADO

# 7. Verificar bitácora
entradas = ticket.bitacora.count()
print(f'7. Bitacora: {entradas} entradas')
for e in ticket.bitacora.all():
    print(f'   [{e.fecha_hora.strftime("%H:%M:%S")}] {e.usuario.username}: {e.accion} | {e.valor_anterior} -> {e.valor_nuevo}')

assert entradas >= 5  # Registro, Clasificación, Asignación, Tomar, Resolver, Cerrar

# 8. Verificar que prioridad_operador NO fue sobrescrita
assert ticket.prioridad_operador == 'Alta'
print()
print('8. prioridad_operador NUNCA fue sobrescrita: OK')

# 9. Verificar campos Fase 2 están vacíos
assert ticket.prioridad_modelo is None
assert ticket.confianza_modelo is None
print('9. Campos de Fase 2 (prioridad_modelo, confianza_modelo) siguen en NULL: OK')

print()
print('=== FLUJO COMPLETO VALIDADO OK ===')
print(f'Ticket {ticket.codigo} paso por todos los estados correctamente.')
