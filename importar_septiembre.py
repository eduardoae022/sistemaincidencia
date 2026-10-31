"""
Script para importar exclusivamente los datos del mes de Septiembre al Sistema de Incidencias.
Limpia los tickets previos de prueba y carga los 180 tickets reales de Septiembre de dataset_09.xlsx
con sus fechas exactas, predicciones del modelo ML y bitacora de auditoria.
"""
import os
import sys
import datetime
from datetime import timedelta
import django
import pandas as pd

# Inicializar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection
from django.utils import timezone
from django.contrib.auth.models import User
from apps.tickets.models import Ticket, BitacoraTicket, Comentario
from apps.catalogos.models import Categoria, ServicioAfectado

EXCEL_PATH = r'c:\Users\User\Desktop\Proyectos\sistema\fase2_machine_learning\data\dataset_09.xlsx'
PRED_PATH = r'c:\Users\User\Desktop\Proyectos\sistema\fase2_machine_learning\resultados\dataset_con_predicciones.csv'

def ejecutar_importacion():
    print('1. Leyendo dataset de Septiembre...')
    df_raw = pd.read_excel(EXCEL_PATH)
    
    # Identificar columnas
    desc_col = [c for c in df_raw.columns if 'Descrip' in c][0]
    cat_col = [c for c in df_raw.columns if 'Categor' in c][0]
    serv_col = [c for c in df_raw.columns if 'Servicio' in c][0]
    prio_op_col = [c for c in df_raw.columns if 'asignada' in c.lower()][0]
    prio_itil_col = [c for c in df_raw.columns if 'correcta' in c.lower()][0]
    sla_max_col = [c for c in df_raw.columns if 'sla m' in c.lower()][0]
    dentro_sla_col = [c for c in df_raw.columns if 'dentro del sla' in c.lower()][0]
    
    df_raw['fecha_reg_dt'] = pd.to_datetime(df_raw['Fecha registro'])
    df_raw['fecha_aten_dt'] = pd.to_datetime(df_raw['Fecha primera atenci\u00f3n'])
    
    # Filtrar solo el mes de septiembre
    df_sep = df_raw[df_raw['fecha_reg_dt'].dt.month == 9].copy().reset_index(drop=True)
    print(f'   Total registros en Septiembre: {len(df_sep)}')

    # Cargar predicciones del modelo
    df_pred = pd.read_csv(PRED_PATH)
    pred_dict = {}
    for _, row in df_pred.iterrows():
        cod = str(row['ID Ticket']).strip()
        prio_pred = str(row['prioridad_predicha']).strip()
        # Confianza mxima
        conf = max(float(row.get('prob_Alta', 0)), float(row.get('prob_Media', 0)), float(row.get('prob_Baja', 0)))
        pred_dict[cod] = (prio_pred, round(conf, 4))

    # Usuarios para asignacion
    solicitante = User.objects.filter(groups__name='Solicitante').first() or User.objects.filter(username='solicitante1').first() or User.objects.first()
    operador = User.objects.filter(groups__name='Operador').first() or User.objects.filter(username='operador1').first() or User.objects.first()
    tecnico = User.objects.filter(groups__name='T\u00e9cnico').first() or User.objects.filter(username='tecnico1').first() or User.objects.first()

    # Mapeo de categorias y servicios
    categorias = {c.nombre.lower().strip(): c for c in Categoria.objects.all()}
    servicios = {s.nombre.lower().strip(): s for s in ServicioAfectado.objects.all()}

    print('2. Limpiando tickets previos en la base de datos...')
    with connection.cursor() as cursor:
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
        cursor.execute("DELETE FROM tickets_comentario")
        cursor.execute("DELETE FROM tickets_bitacoraticket")
        cursor.execute("DELETE FROM tickets_ticket")
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
    print('   Base de datos de tickets limpia.')

    print('3. Insertando los 180 tickets de Septiembre...')
    tz = timezone.get_current_timezone()
    
    creados = 0
    bitacoras_creadas = 0

    for _, row in df_sep.iterrows():
        cod_str = str(row['ID Ticket']).strip()
        pk_num = int(cod_str.replace('TK-', ''))
        
        cat_nombre = str(row[cat_col]).strip()
        cat_obj = categorias.get(cat_nombre.lower())
        
        serv_nombre = str(row[serv_col]).strip()
        serv_obj = servicios.get(serv_nombre.lower())
        
        prio_op = str(row[prio_op_col]).strip()
        prio_itil = str(row[prio_itil_col]).strip()
        
        # Parsear SLA max
        sla_str = str(row[sla_max_col]).replace('h', '').strip()
        sla_max_h = int(float(sla_str)) if sla_str else 24
        
        # Parsear dentro SLA
        dentro_sla = str(row[dentro_sla_col]).strip().lower() in ['s\u00ed', 'si', '1', 'true', 's']
        
        # Parsear horas transcurridas y fecha cierre
        horas_str = str(row['Horas transcurridas']).replace('h', '').strip()
        horas_trans = float(horas_str) if horas_str else 24.0
        
        dt_reg = timezone.make_aware(row['fecha_reg_dt'].to_pydatetime(), tz)
        dt_aten = timezone.make_aware(row['fecha_aten_dt'].to_pydatetime(), tz) if pd.notnull(row['fecha_aten_dt']) else dt_reg + timedelta(minutes=15)
        dt_cierre = dt_reg + timedelta(hours=horas_trans)

        # Prediccion ML
        if cod_str in pred_dict:
            prio_mod, conf_mod = pred_dict[cod_str]
            siguio_ia = (prio_op == prio_mod)
        else:
            prio_mod, conf_mod, siguio_ia = None, None, None

        # Crear Ticket
        ticket = Ticket(
            id=pk_num,
            descripcion=str(row[desc_col]).strip(),
            categoria=cat_obj,
            servicio_afectado=serv_obj,
            solicitante=solicitante,
            tecnico_asignado=tecnico,
            prioridad_operador=prio_op,
            prioridad_correcta=prio_itil,
            prioridad_modelo=prio_mod,
            confianza_modelo=conf_mod,
            siguio_sugerencia_ia=siguio_ia,
            estado=Ticket.ESTADO_CERRADO,
            fecha_hora_primera_atencion=dt_aten,
            fecha_hora_cierre=dt_cierre,
            sla_maximo_horas=sla_max_h,
            dentro_sla=dentro_sla,
            solucion_aplicada='Incidencia resuelta satisfactoriamente siguiendo el protocolo t\u00e9cnico correspondiente.',
            es_reapertura=False,
        )
        ticket.save(force_insert=True)
        # Actualizar fecha de registro exacta saltando auto_now_add
        Ticket.objects.filter(id=pk_num).update(fecha_hora_registro=dt_reg)

        # Crear entradas de bitacora
        b_reg = BitacoraTicket.objects.create(
            ticket=ticket,
            usuario=solicitante,
            accion='Registro',
            detalle='Registro de incidencia desde portal',
            valor_anterior='',
            valor_nuevo='Registrado'
        )
        BitacoraTicket.objects.filter(id=b_reg.id).update(fecha_hora=dt_reg)

        b_clasif = BitacoraTicket.objects.create(
            ticket=ticket,
            usuario=operador,
            accion='Clasificaci\u00f3n',
            detalle=f'Categor\u00eda: {cat_nombre}, Servicio: {serv_nombre}, Prioridad: {prio_op}, SLA: {sla_max_h}h',
            valor_anterior='Registrado',
            valor_nuevo='Clasificado'
        )
        BitacoraTicket.objects.filter(id=b_clasif.id).update(fecha_hora=dt_reg + timedelta(minutes=2))

        if prio_mod:
            b_ia = BitacoraTicket.objects.create(
                ticket=ticket,
                usuario=operador,
                accion='Sugerencia IA',
                detalle=f'Sugerencia del modelo Random Forest: {prio_mod} (confianza: {conf_mod*100:.1f}%)',
                valor_anterior='',
                valor_nuevo=prio_mod
            )
            BitacoraTicket.objects.filter(id=b_ia.id).update(fecha_hora=dt_reg + timedelta(minutes=2))

        b_asig = BitacoraTicket.objects.create(
            ticket=ticket,
            usuario=operador,
            accion='Asignaci\u00f3n de t\u00e9cnico',
            detalle=f'T\u00e9cnico: {tecnico.get_full_name() or tecnico.username}',
            valor_anterior='Sin asignar',
            valor_nuevo=tecnico.get_full_name() or tecnico.username
        )
        BitacoraTicket.objects.filter(id=b_asig.id).update(fecha_hora=dt_reg + timedelta(minutes=5))

        b_aten = BitacoraTicket.objects.create(
            ticket=ticket,
            usuario=tecnico,
            accion='Inicio de atenci\u00f3n',
            detalle='T\u00e9cnico toma el ticket e inicia las labores de soporte',
            valor_anterior='Asignado',
            valor_nuevo='En atenci\u00f3n'
        )
        BitacoraTicket.objects.filter(id=b_aten.id).update(fecha_hora=dt_aten)

        b_res = BitacoraTicket.objects.create(
            ticket=ticket,
            usuario=tecnico,
            accion='Resoluci\u00f3n',
            detalle='Incidencia resuelta satisfactoriamente.',
            valor_anterior='En atenci\u00f3n',
            valor_nuevo='Resuelto'
        )
        BitacoraTicket.objects.filter(id=b_res.id).update(fecha_hora=dt_cierre - timedelta(minutes=5))

        b_cie = BitacoraTicket.objects.create(
            ticket=ticket,
            usuario=operador,
            accion='Cierre',
            detalle='Ticket cerrado y verificado con el usuario.',
            valor_anterior='Resuelto',
            valor_nuevo='Cerrado'
        )
        BitacoraTicket.objects.filter(id=b_cie.id).update(fecha_hora=dt_cierre)

        creados += 1
        bitacoras_creadas += 7

    print(f'4. Importacion finalizada con exito:')
    print(f'   - Tickets incorporados: {creados}')
    print(f'   - Entradas de bitacora: {bitacoras_creadas}')
    print(f'   - Rango: TK-1105 a TK-1284')

if __name__ == '__main__':
    ejecutar_importacion()
