"""
Management command: cargar datos iniciales del sistema.
Uso: python manage.py cargar_datos_iniciales

Crea:
- 4 grupos/roles: Solicitante, Operador, Técnico, Administrador
- 1 usuario por rol con contraseñas por defecto
- 5 categorías: Red, Base de Datos, Aplicación, Hardware, Seguridad
- Servicios afectados de ejemplo
- 3 valores de SLA: Alta=4h, Media=24h, Baja=72h
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group
from apps.catalogos.models import Categoria, ServicioAfectado, SLA
from apps.usuarios.models import PerfilUsuario


class Command(BaseCommand):
    help = 'Carga los datos iniciales del sistema (roles, usuarios, catálogos, SLA)'

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING('=== Cargando datos iniciales del sistema ==='))

        # ── 1. Grupos / Roles ────────────────────────────────────────────────
        self.stdout.write('  Creando grupos de roles...')
        roles = ['Solicitante', 'Operador', 'Técnico', 'Administrador']
        grupos = {}
        for rol in roles:
            grupo, created = Group.objects.get_or_create(name=rol)
            grupos[rol] = grupo
            estado = self.style.SUCCESS('creado') if created else 'ya existía'
            self.stdout.write(f'    Rol "{rol}": {estado}')

        # ── 2. Usuarios de prueba ────────────────────────────────────────────
        self.stdout.write('  Creando usuarios de prueba...')
        usuarios_seed = [
            {
                'username': 'solicitante1',
                'first_name': 'Carlos',
                'last_name': 'Pérez',
                'email': 'solicitante@urbinmobiliaria.com',
                'password': 'Solicitante2024!',
                'rol': 'Solicitante',
                'area': 'Contabilidad',
            },
            {
                'username': 'operador1',
                'first_name': 'Ana',
                'last_name': 'García',
                'email': 'operador@urbinmobiliaria.com',
                'password': 'Operador2024!',
                'rol': 'Operador',
                'area': 'Mesa de Ayuda',
            },
            {
                'username': 'tecnico1',
                'first_name': 'Luis',
                'last_name': 'Martínez',
                'email': 'tecnico@urbinmobiliaria.com',
                'password': 'Tecnico2024!',
                'rol': 'Técnico',
                'area': 'Soporte Técnico',
            },
            {
                'username': 'admin1',
                'first_name': 'María',
                'last_name': 'López',
                'email': 'admin@urbinmobiliaria.com',
                'password': 'Admin2024!',
                'rol': 'Administrador',
                'area': 'Administración de Sistemas',
            },
        ]

        for datos in usuarios_seed:
            user, created = User.objects.get_or_create(username=datos['username'])
            if created:
                user.first_name = datos['first_name']
                user.last_name = datos['last_name']
                user.email = datos['email']
                user.set_password(datos['password'])
                user.save()
                user.groups.set([grupos[datos['rol']]])
                perfil, _ = PerfilUsuario.objects.get_or_create(usuario=user)
                perfil.area = datos['area']
                perfil.save()
                self.stdout.write(f'    Usuario "{datos["username"]}" ({datos["rol"]}): {self.style.SUCCESS("creado")} — contraseña: {datos["password"]}')
            else:
                self.stdout.write(f'    Usuario "{datos["username"]}": ya existía')

        # ── 3. Categorías ────────────────────────────────────────────────────
        self.stdout.write('  Creando categorías...')
        categorias_seed = [
            'Aplicación',
            'Hardware',
            'Red',
            'Seguridad',
        ]
        categorias = {}
        for nombre in categorias_seed:
            cat, created = Categoria.objects.get_or_create(nombre=nombre, defaults={'activo': True})
            cat.activo = True
            cat.save()
            categorias[nombre] = cat
            estado = self.style.SUCCESS('creada') if created else 'ya existía'
            self.stdout.write(f'    Categoría "{nombre}": {estado}')

        # ── 4. Servicios afectados ───────────────────────────────────────────
        self.stdout.write('  Creando servicios afectados (catálogo oficial URBINMOBILIARIA)...')
        servicios_seed = [
            # Aplicación (6)
            ('CRM inmobiliario', 'Aplicación'),
            ('Generador de contratos', 'Aplicación'),
            ('Módulo de reportes', 'Aplicación'),
            ('Módulo de seguimiento de clientes', 'Aplicación'),
            ('Sistema de firma digital de contratos', 'Aplicación'),
            ('Sistema de gestión documental', 'Aplicación'),
            # Hardware (7)
            ('Batería de laptop', 'Hardware'),
            ('Cámara web', 'Hardware'),
            ('Equipo de escritorio', 'Hardware'),
            ('Impresora local', 'Hardware'),
            ('Laptop corporativa', 'Hardware'),
            ('Monitor', 'Hardware'),
            ('Periféricos (teclado/mouse)', 'Hardware'),
            # Red (8)
            ('Carpeta compartida', 'Red'),
            ('Conectividad de oficina', 'Red'),
            ('Correo corporativo (Outlook)', 'Red'),
            ('Enlace a internet', 'Red'),
            ('Impresora de red', 'Red'),
            ('Red interna', 'Red'),
            ('Red Wi-Fi', 'Red'),
            ('Servidor de archivos', 'Red'),
            # Seguridad (8)
            ('Active Directory', 'Seguridad'),
            ('Antivirus corporativo', 'Seguridad'),
            ('Carpeta de contratos compartida', 'Seguridad'),
            ('Certificados digitales', 'Seguridad'),
            ('Correo corporativo', 'Seguridad'),
            ('Firewall perimetral', 'Seguridad'),
            ('Sistema de autenticación (MFA)', 'Seguridad'),
            ('VPN corporativa', 'Seguridad'),
        ]
        for nombre, cat_nombre in servicios_seed:
            cat = categorias.get(cat_nombre)
            if cat:
                serv, created = ServicioAfectado.objects.get_or_create(
                    nombre=nombre,
                    categoria=cat,
                    defaults={'activo': True}
                )
                serv.activo = True
                serv.save()
                estado = self.style.SUCCESS('creado') if created else 'ya existía'
                self.stdout.write(f'    Servicio "{nombre}" ({cat_nombre}): {estado}')

        # ── 5. SLA ───────────────────────────────────────────────────────────
        self.stdout.write('  Configurando SLA...')
        sla_seed = [
            ('Alta', 4),
            ('Media', 24),
            ('Baja', 72),
        ]
        for prioridad, horas in sla_seed:
            sla, created = SLA.objects.get_or_create(
                prioridad=prioridad,
                defaults={'horas_maximas': horas}
            )
            if created:
                self.stdout.write(f'    SLA {prioridad}: {horas}h — {self.style.SUCCESS("creado")}')
            else:
                self.stdout.write(f'    SLA {prioridad}: {sla.horas_maximas}h — ya existía')

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('>>> Datos iniciales cargados exitosamente.'))
        self.stdout.write('')
        self.stdout.write('  Credenciales de acceso:')
        self.stdout.write('    solicitante1 / Solicitante2024!')
        self.stdout.write('    operador1    / Operador2024!')
        self.stdout.write('    tecnico1     / Tecnico2024!')
        self.stdout.write('    admin1       / Admin2024!')
        self.stdout.write('')
        self.stdout.write(self.style.WARNING('  ATENCION: Cambie las contrasenas en produccion.'))
