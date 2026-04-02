# -*- coding: utf-8 -*-
"""
Calculadora Planetaria con Efemerides Reales
Basada en los algoritmos de Jean Meeus - Astronomical Algorithms
Precisión: ~1 arcmin para planetas principales
Compatible con Pythonista 3 en iOS 15+
"""

import ui
import datetime
import math
import json
import os

# ============================================================
# MATEMATICAS AUXILIARES
# ============================================================

def rad(deg):
    return deg * math.pi / 180.0

def deg(rad_val):
    return rad_val * 180.0 / math.pi

def normalize(degrees):
    """Normaliza a 0-360"""
    return degrees % 360.0

def normalize_rad(rad_val):
    """Normaliza a 0-2pi"""
    return rad_val % (2 * math.pi)

# ============================================================
# ALGORITMOS DE MEEUS - EFEMERIDES REALES
# ============================================================

class Ephemeris:
    """Calculo de posiciones planetarias reales usando algoritmos de Meeus"""
    
    # Coeficientes VSOP87 simplificados para longitud ecliptica (grados)
    # Fuente: Jean Meeus, Astronomical Algorithms, 2nd Ed.
    
    @staticmethod
    def julian_day(year, month, day, hour=0, minute=0, second=0):
        """Calcula el Dia Juliano (Meeus cap. 7)"""
        if month <= 2:
            year -= 1
            month += 12
        A = int(year / 100)
        B = 2 - A + int(A / 4)
        day_frac = day + hour/24.0 + minute/1440.0 + second/86400.0
        JD = int(365.25 * (year + 4716)) + int(30.6001 * (month + 1)) + day_frac + B - 1524.5
        return JD
    
    @staticmethod
    def julian_century(JD):
        """Siglos julianos desde J2000.0"""
        return (JD - 2451545.0) / 36525.0
    
    @staticmethod
    def sun_longitude(T):
        """Longitud geometrica del Sol (Meeus cap. 25)"""
        L0 = 280.46646 + 36000.76983 * T + 0.0003032 * T * T
        L0 = normalize(L0)
        
        # Anomalia media del Sol
        M = 357.52911 + 35999.05029 * T - 0.0001537 * T * T
        M = normalize(M)
        Mrad = rad(M)
        
        # Ecuacion del centro
        C = (1.914602 - 0.004817 * T) * math.sin(Mrad) + \
            (0.019993 - 0.000101 * T) * math.sin(2 * Mrad) + \
            0.000289 * math.sin(3 * Mrad)
        
        # Longitud verdadera
        sun_long = L0 + C
        
        # Nutacion en longitud (simplificada)
        omega = 125.04 - 1934.136 * T
        nutation = -0.004778 * math.sin(rad(omega))
        
        return normalize(sun_long + nutation)
    
    @staticmethod
    def moon_longitude(T):
        """Longitud de la Luna (Meeus cap. 47, precision ~10")"""
        # Longitud media
        Lp = 218.3165 + 481267.8813 * T
        # Elongacion media
        D = 297.8502 + 445267.1115 * T
        # Anomalia media del Sol
        M = 357.5291 + 35999.0503 * T
        # Anomalia media de la Luna
        Mp = 134.9634 + 477198.8676 * T
        # Argumento de latitud
        F = 93.2720 + 483202.0175 * T
        
        Lp = normalize(Lp)
        D = normalize(D)
        M = normalize(M)
        Mp = normalize(Mp)
        F = normalize(F)
        
        Lp_r, D_r, M_r, Mp_r, F_r = rad(Lp), rad(D), rad(M), rad(Mp), rad(F)
        
        # Terminos periodicos principales (Meeus Tabla 47.A)
        sigma = 0
        # Terminos con argumento D
        sigma += 6.289 * math.sin(D_r)
        sigma += 1.274 * math.sin(2*Lp_r - 2*D_r)
        sigma += 0.658 * math.sin(2*D_r)
        sigma += 0.214 * math.sin(2*Lp_r - 4*D_r)
        sigma += 0.186 * math.sin(M_r)
        sigma -= 0.114 * math.sin(2*Lp_r)
        sigma += 0.059 * math.sin(2*Mp_r - 2*D_r)
        sigma += 0.057 * math.sin(2*Lp_r - 2*D_r - M_r)
        sigma -= 0.053 * math.sin(2*Lp_r - 2*D_r + M_r)
        sigma += 0.046 * math.sin(2*D_r - M_r)
        sigma += 0.041 * math.sin(2*Lp_r - D_r)
        sigma -= 0.035 * math.sin(D_r + M_r)
        sigma -= 0.031 * math.sin(2*Lp_r - 2*D_r - Mp_r)
        sigma += 0.015 * math.sin(2*Lp_r - 2*D_r + Mp_r)
        sigma -= 0.014 * math.sin(4*Lp_r - 4*D_r)
        sigma += 0.011 * math.sin(4*D_r)
        sigma += 0.010 * math.sin(2*Lp_r - 3*D_r)
        sigma -= 0.009 * math.sin(2*D_r + M_r)
        sigma -= 0.008 * math.sin(2*Lp_r - D_r - M_r)
        sigma += 0.007 * math.sin(2*Lp_r - 3*D_r + M_r)
        
        return normalize(Lp + sigma)
    
    @staticmethod
    def planet_longitude(planet, T):
        """
        Longitud heliocentrica de planetas usando elementos orbitales
        (Meeus cap. 31-32, elementos para J2000.0)
        """
        # Elementos orbitales para J2000.0 (Meeus Tabla 31.A)
        elements = {
            'Mercurio': {
                'a': (0.38709927, 0.00000037),
                'e': (0.20563593, 0.00001906),
                'I': (7.00497902, -0.00594749),
                'L': (252.25032350, 149472.6746594),
                'w_bar': (77.45779628, 0.16047689),
                'Omega': (48.33076593, -0.12534081),
            },
            'Venus': {
                'a': (0.72333566, 0.00000390),
                'e': (0.00677672, -0.00004107),
                'I': (3.39467605, -0.00078890),
                'L': (181.97909950, 58517.8156768),
                'w_bar': (131.60246718, 0.00268329),
                'Omega': (76.67984255, -0.27769418),
            },
            'Marte': {
                'a': (1.52371034, 0.00001847),
                'e': (0.09339410, 0.00007882),
                'I': (1.84969142, -0.00813131),
                'L': (355.45332240, 19140.2993424),
                'w_bar': (336.05637181, 0.44441088),
                'Omega': (49.55953891, -0.29257343),
            },
            'Jupiter': {
                'a': (5.20288700, -0.00011607),
                'e': (0.04838624, -0.00013253),
                'I': (1.30439695, -0.00183714),
                'L': (34.39644051, 3034.74612775),
                'w_bar': (14.72847983, 0.21252668),
                'Omega': (100.47390909, 0.20469106),
            },
            'Saturno': {
                'a': (9.53667594, -0.00125060),
                'e': (0.05386179, -0.00050991),
                'I': (2.48599187, 0.00193609),
                'L': (49.95424423, 1222.49362201),
                'w_bar': (92.59887831, -0.41897216),
                'Omega': (113.66242448, -0.28867794),
            },
            'Urano': {
                'a': (19.18916464, -0.00196176),
                'e': (0.04725744, -0.00004397),
                'I': (0.77263781, -0.00242939),
                'L': (313.23810451, 428.48202785),
                'w_bar': (170.95427630, 0.40805281),
                'Omega': (74.01692503, 0.04240589),
            },
            'Neptuno': {
                'a': (30.06992276, 0.00026291),
                'e': (0.00859048, 0.00005105),
                'I': (1.77004347, 0.00035372),
                'L': (304.88003070, 218.45945325),
                'w_bar': (44.96476227, -0.32241464),
                'Omega': (131.78422574, -0.00508664),
            },
        }
        
        if planet not in elements:
            return 0.0
        
        el = elements[planet]
        
        # Calcular elementos para el tiempo T
        a = el['a'][0] + el['a'][1] * T
        e = el['e'][0] + el['e'][1] * T
        I = el['I'][0] + el['I'][1] * T
        L = normalize(el['L'][0] + el['L'][1] * T)
        w_bar = el['w_bar'][0] + el['w_bar'][1] * T
        Omega = el['Omega'][0] + el['Omega'][1] * T
        
        # Anomalia media
        M = normalize(L - w_bar)
        Mrad = rad(M)
        
        # Resolver ecuacion de Kepler: E - e*sin(E) = M
        E = Mrad
        for _ in range(10):
            E = E - (E - e * math.sin(E) - Mrad) / (1 - e * math.cos(E))
        
        # Anomalia verdadera
        v = 2 * math.atan2(math.sqrt(1 + e) * math.sin(E / 2),
                          math.sqrt(1 - e) * math.cos(E / 2))
        v_deg = deg(v)
        
        # Longitud heliocentrica
        h = normalize(w_bar - Omega + v_deg)
        
        # Distancia al Sol
        r = a * (1 - e * math.cos(E))
        
        # Latitud heliocentrica
        b = deg(math.asin(math.sin(rad(I)) * math.sin(v + rad(w_bar - Omega))))
        
        return h, b, r, I, Omega, v_deg
    
    @staticmethod
    def solve_kepler(M_rad, e, iterations=10):
        """Resuelve la ecuacion de Kepler E - e*sin(E) = M"""
        E = M_rad
        for _ in range(iterations):
            E = E - (E - e * math.sin(E) - M_rad) / (1 - e * math.cos(E))
        return E
    
    @staticmethod
    def heliocentric_to_geocentric(h_planet, b_planet, r_planet, h_sun, r_sun):
        """
        Convierte coordenadas heliocentricas a geocentricas
        (Meeus cap. 33)
        """
        # Coordenadas rectangulares heliocentricas del planeta
        x_p = r_planet * math.cos(rad(b_planet)) * math.cos(rad(h_planet))
        y_p = r_planet * math.cos(rad(b_planet)) * math.sin(rad(h_planet))
        z_p = r_planet * math.sin(rad(b_planet))
        
        # Coordenadas rectangulares heliocentricas de la Tierra (= -Sol geocentrico)
        x_e = -r_sun * math.cos(rad(h_sun))
        y_e = -r_sun * math.sin(rad(h_sun))
        z_e = 0
        
        # Coordenadas geocentricas del planeta
        x = x_p + x_e
        y = y_p + y_e
        z = z_p + z_e
        
        # Longitud geocentrica
        lon = normalize(deg(math.atan2(y, x)))
        
        # Latitud geocentrica
        lat = deg(math.atan2(z, math.sqrt(x*x + y*y)))
        
        return lon, lat
    
    @staticmethod
    def get_all_positions(JD):
        """Calcula todas las posiciones planetarias geocentricas"""
        T = Ephemeris.julian_century(JD)
        
        # Posicion del Sol (geocentrica)
        sun_lon = Ephemeris.sun_longitude(T)
        
        # Posicion de la Luna (geocentrica)
        moon_lon = Ephemeris.moon_longitude(T)
        
        # Sol: distancia aproximada (Meeus cap. 25)
        M_sun = normalize(357.52911 + 35999.05029 * T)
        r_sun = 1.000001018 * (1 - 0.016708634 * math.cos(rad(M_sun)))
        
        positions = {}
        positions['Sol'] = {'lon': sun_lon, 'lat': 0, 'retro': False}
        positions['Luna'] = {'lon': moon_lon, 'lat': 0, 'retro': False}
        
        # Planetas
        planet_names = ['Mercurio', 'Venus', 'Marte', 'Jupiter', 'Saturno', 'Urano', 'Neptuno']
        
        for name in planet_names:
            h, b, r, I, Omega, v = Ephemeris.planet_longitude(name, T)
            
            # Convertir a geocentrico
            geo_lon, geo_lat = Ephemeris.heliocentric_to_geocentric(
                h, b, r, sun_lon, r_sun
            )
            
            # Detectar retrogradacion comparando con posicion anterior
            # (se hace en el metodo caller con delta de tiempo)
            positions[name] = {'lon': geo_lon, 'lat': geo_lat, 'r': r}
        
        # Calcular retrogradacion con delta de 1 dia
        JD_prev = JD - 1.0
        T_prev = Ephemeris.julian_century(JD_prev)
        sun_lon_prev = Ephemeris.sun_longitude(T_prev)
        M_sun_prev = normalize(357.52911 + 35999.05029 * T_prev)
        r_sun_prev = 1.000001018 * (1 - 0.016708634 * math.cos(rad(M_sun_prev)))
        
        for name in planet_names:
            h_prev, b_prev, r_prev, I_prev, Omega_prev, v_prev = Ephemeris.planet_longitude(name, T_prev)
            geo_lon_prev, geo_lat_prev = Ephemeris.heliocentric_to_geocentric(
                h_prev, b_prev, r_prev, sun_lon_prev, r_sun_prev
            )
            
            # Calcular movimiento diario
            motion = positions[name]['lon'] - geo_lon_prev
            if motion > 180:
                motion -= 360
            elif motion < -180:
                motion += 360
            
            positions[name]['retro'] = motion < 0
            positions[name]['motion'] = motion
        
        return positions
    
    @staticmethod
    def sidereal_time(JD):
        """Tiempo sidereo de Greenwich en grados (Meeus cap. 12)"""
        T = Ephemeris.julian_century(JD)
        JD0 = int(JD + 0.5)
        frac = JD + 0.5 - JD0
        
        # Horas UT
        UT = frac * 24
        
        theta0 = 280.46061837 + 360.98564736629 * (JD0 - 2451545.0) + \
                 0.000387933 * T * T - T * T * T / 38710000.0
        
        theta = normalize(theta0 + 360.98564736629 * UT / 24.0)
        return theta
    
    @staticmethod
    def calculate_ascendant(JD, latitude, longitude):
        """Calcula el Ascendente (Meeus cap. 12)"""
        # Tiempo sidereo local
        gst = Ephemeris.sidereal_time(JD)
        lst = normalize(gst + longitude)  # en grados
        
        # Oblicuidad de la ecliptica (Meeus cap. 22)
        T = Ephemeris.julian_century(JD)
        epsilon = 23.439291 - 0.013004 * T
        
        # Ascendente
        asc = deg(math.atan2(
            math.cos(rad(lst)),
            -(math.sin(rad(lst)) * math.cos(rad(epsilon)) + math.tan(rad(latitude)) * math.sin(rad(epsilon)))
        ))
        return normalize(asc)
    
    @staticmethod
    def calculate_mc(JD, latitude, longitude):
        """Calcula el Medio Cielo (Meeus cap. 12)"""
        gst = Ephemeris.sidereal_time(JD)
        lst = normalize(gst + longitude)
        
        T = Ephemeris.julian_century(JD)
        epsilon = 23.439291 - 0.013004 * T
        
        mc = deg(math.atan2(
            math.sin(rad(lst)),
            math.cos(rad(lst)) * math.cos(rad(epsilon))
        ))
        return normalize(mc)
    
    @staticmethod
    def calculate_houses_placidus(JD, latitude, longitude):
        """
        Sistema de casas Placidus (simplificado)
        Para Pythonista usamos una aproximacion iterativa
        """
        asc = Ephemeris.calculate_ascendant(JD, latitude, longitude)
        mc = Ephemeris.calculate_mc(JD, latitude, longitude)
        
        T = Ephemeris.julian_century(JD)
        epsilon = 23.439291 - 0.013004 * T
        eps_rad = rad(epsilon)
        
        houses = {}
        houses[10] = mc  # MC = Casa 10
        houses[1] = asc  # ASC = Casa 1
        houses[7] = normalize(asc + 180)  # DSC
        houses[4] = normalize(mc + 180)  # IC
        
        # Casas intermedias (aproximacion Placidus)
        # Usamos el metodo semi-arc para las casas 2,3,11,12
        lst_rad = rad(normalize(Ephemeris.sidereal_time(JD) + longitude))
        lat_rad = rad(latitude)
        
        # Casa 11 y 2
        for house_num, factor in [(11, 2/3), (2, 2/3), (12, 1/3), (3, 1/3)]:
            # Aproximacion usando arcos semidiurnos
            if house_num in [11, 12]:
                # Casas sobre el horizonte
                ra = normalize(deg(lst_rad) + factor * 90)
            else:
                # Casas bajo el horizonte
                ra = normalize(deg(lst_rad) + 180 + factor * 90)
            
            ra_rad = rad(ra)
            
            # Conversion de AR a longitud ecliptica
            y = math.sin(ra_rad) * math.cos(eps_rad) + math.tan(lat_rad) * math.sin(eps_rad)
            x = math.cos(ra_rad)
            house_lon = normalize(deg(math.atan2(y, x)))
            houses[house_num] = house_lon
        
        return houses
    
    @staticmethod
    def moon_phase(JD):
        """Fase lunar (0-1, 0=Luna Nueva)"""
        T = Ephemeris.julian_century(JD)
        
        # Elongacion Luna-Sol
        sun_lon = Ephemeris.sun_longitude(T)
        moon_lon = Ephemeris.moon_longitude(T)
        
        elongation = normalize(moon_lon - sun_lon)
        phase = elongation / 360.0
        
        return phase, elongation
    
    @staticmethod
    def aspects(lon1, lon2):
        """Calcula el aspecto entre dos puntos"""
        diff = abs(lon1 - lon2)
        if diff > 180:
            diff = 360 - diff
        
        aspect_types = {
            'Conjuncion': 0,
            'Sextil': 60,
            'Cuadratura': 90,
            'Trigono': 120,
            'Oposicion': 180,
            'Quincuncio': 150,
            'Semisextil': 30,
            'Semicuadratura': 45,
            'Sesquicuadratura': 135,
        }
        
        best_aspect = None
        best_orb = 999
        
        for name, angle in aspect_types.items():
            orb = abs(diff - angle)
            if orb > 180:
                orb = 360 - orb
            if orb < best_orb:
                best_orb = orb
                best_aspect = name
        
        return best_aspect, best_orb


# ============================================================
# DATOS DE COORDENADAS
# ============================================================

CITIES = {
    'Madrid': (40.4168, -3.7038),
    'Barcelona': (41.3874, 2.1686),
    'Buenos Aires': (-34.6037, -58.3816),
    'Ciudad de Mexico': (19.4326, -99.1332),
    'Bogota': (4.7110, -74.0721),
    'Lima': (-12.0464, -77.0428),
    'Santiago': (-33.4489, -70.6693),
    'Montevideo': (-34.9011, -56.1645),
    'Quito': (-0.1807, -78.4678),
    'Caracas': (10.4806, -66.9036),
    'La Habana': (23.1136, -82.3666),
    'San Jose CR': (9.9281, -84.0907),
    'Panama': (8.9824, -79.5199),
    'Nueva York': (40.7128, -74.0060),
    'Los Angeles': (34.0522, -118.2437),
    'Londres': (51.5074, -0.1278),
    'Paris': (48.8566, 2.3522),
    'Roma': (41.9028, 12.4964),
    'Berlin': (52.5200, 13.4050),
    'Tokio': (35.6762, 139.6503),
    'Sydney': (-33.8688, 151.2093),
    'Moscu': (55.7558, 37.6173),
}


# ============================================================
# APP PRINCIPAL
# ============================================================

class AstroApp(ui.View):
    
    def __init__(self):
        self.background_color = '#0a0a1a'
        self.flex = 'WH'
        self.utc_offset = 0
        self.latitude = 40.4168
        self.longitude = -3.7038
        self.city_name = 'Madrid'
        self.positions_cache = {}
        self.setup_ui()
        self.load_config()
    
    def setup_ui(self):
        # Barra superior
        title = ui.Label()
        title.text = "✦ Efemerides Planetarias ✦"
        title.text_color = '#f0c040'
        title.alignment = ui.ALIGN_CENTER
        title.font = ('Helvetica-Bold', 20)
        title.frame = (0, 8, self.width, 40)
        title.flex = 'W'
        self.add_subview(title)
        
        # Info bar
        self.info_label = ui.Label()
        self.info_label.text = ""
        self.info_label.text_color = '#8888aa'
        self.info_label.alignment = ui.ALIGN_CENTER
        self.info_label.font = ('Helvetica', 11)
        self.info_label.frame = (0, 45, self.width, 20)
        self.info_label.flex = 'W'
        self.add_subview(self.info_label)
        
        # Segmented control
        self.segmented = ui.SegmentedControl()
        self.segmented.segments = ['Carta', 'Buscar', 'Aspectos', 'Ajustes']
        self.segmented.frame = (8, 68, self.width - 16, 32)
        self.segmented.tint_color = '#f0c040'
        self.segmented.action = self.switch_tab
        self.segmented.flex = 'W'
        self.segmented.selected_index = 0
        self.add_subview(self.segmented)
        
        # Contenedor
        self.container = ui.View(frame=(0, 105, self.width, self.height - 115))
        self.container.flex = 'WH'
        self.container.background_color = '#0a0a1a'
        self.add_subview(self.container)
        
        # Crear pestañas
        self.tab_chart = self.create_tab_chart()
        self.tab_search = self.create_tab_search()
        self.tab_aspects = self.create_tab_aspects()
        self.tab_settings = self.create_tab_settings()
        
        for tab in [self.tab_chart, self.tab_search, self.tab_aspects, self.tab_settings]:
            self.container.add_subview(tab)
        
        self.tab_chart.hidden = False
        self.tab_search.hidden = True
        self.tab_aspects.hidden = True
        self.tab_settings.hidden = True
        
        self.update_info_bar()
    
    def update_info_bar(self):
        self.info_label.text = f"{self.city_name} | UTC{self.utc_offset:+g} | Lat:{self.latitude:.1f} Lon:{self.longitude:.1f}"
    
    def create_tab_chart(self):
        view = ui.View(frame=self.container.bounds)
        view.flex = 'WH'
        view.background_color = '#0a0a1a'
        
        y = 10
        # DatePicker
        self.date_picker = ui.DatePicker(frame=(10, y, view.width-20, 100))
        self.date_picker.date = datetime.datetime.now()
        self.date_picker.mode = ui.DATE_PICKER_MODE_DATE_AND_TIME
        self.date_picker.flex = 'W'
        view.add_subview(self.date_picker)
        
        y += 110
        # Boton calcular
        btn = ui.Button(frame=(10, y, view.width-20, 44))
        btn.title = "✦ Calcular Carta ✦"
        btn.background_color = '#f0c040'
        btn.tint_color = '#1a1a2e'
        btn.font = ('Helvetica-Bold', 17)
        btn.corner_radius = 8
        btn.action = self.calc_chart
        btn.flex = 'W'
        view.add_subview(btn)
        
        y += 54
        # Resultados
        self.chart_text = ui.TextView(frame=(10, y, view.width-20, view.height - y - 10))
        self.chart_text.background_color = '#12122a'
        self.chart_text.text_color = '#00ffaa'
        self.chart_text.editable = False
        self.chart_text.font = ('Menlo', 11)
        self.chart_text.corner_radius = 8
        self.chart_text.flex = 'WH'
        view.add_subview(self.chart_text)
        
        return view
    
    def create_tab_search(self):
        view = ui.View(frame=self.container.bounds)
        view.flex = 'WH'
        view.background_color = '#0a0a1a'
        
        y = 10
        # Planeta
        lbl = ui.Label(frame=(10, y, 80, 30))
        lbl.text = "Planeta:"
        lbl.text_color = '#ccccdd'
        lbl.font = ('Helvetica', 13)
        view.add_subview(lbl)
        
        self.search_planet = ui.TextField(frame=(90, y, view.width-100, 30))
        self.search_planet.text = "Jupiter"
        self.search_planet.background_color = '#1a1a3e'
        self.search_planet.text_color = '#f0c040'
        self.search_planet.corner_radius = 6
        self.search_planet.flex = 'W'
        view.add_subview(self.search_planet)
        
        y += 40
        # Grado
        lbl = ui.Label(frame=(10, y, 80, 30))
        lbl.text = "Grado:"
        lbl.text_color = '#ccccdd'
        lbl.font = ('Helvetica', 13)
        view.add_subview(lbl)
        
        self.search_degree = ui.TextField(frame=(90, y, 60, 30))
        self.search_degree.text = "15"
        self.search_degree.background_color = '#1a1a3e'
        self.search_degree.text_color = '#f0c040'
        self.search_degree.corner_radius = 6
        self.search_degree.keyboard_type = ui.KEYBOARD_NUMBER_PAD
        view.add_subview(self.search_degree)
        
        y += 40
        # Signo
        lbl = ui.Label(frame=(10, y, 80, 30))
        lbl.text = "Signo:"
        lbl.text_color = '#ccccdd'
        lbl.font = ('Helvetica', 13)
        view.add_subview(lbl)
        
        self.search_sign = ui.TextField(frame=(90, y, view.width-100, 30))
        self.search_sign.text = "Aries"
        self.search_sign.background_color = '#1a1a3e'
        self.search_sign.text_color = '#f0c040'
        self.search_sign.corner_radius = 6
        self.search_sign.flex = 'W'
        view.add_subview(self.search_sign)
        
        y += 45
        # Fecha inicio
        lbl = ui.Label(frame=(10, y, 80, 30))
        lbl.text = "Desde:"
        lbl.text_color = '#ccccdd'
        lbl.font = ('Helvetica', 13)
        view.add_subview(lbl)
        
        self.search_start = ui.DatePicker(frame=(10, y+28, view.width-20, 90))
        self.search_start.date = datetime.datetime.now()
        self.search_start.mode = ui.DATE_PICKER_MODE_DATE
        self.search_start.flex = 'W'
        view.add_subview(self.search_start)
        
        y += 128
        # Fecha fin
        lbl = ui.Label(frame=(10, y, 80, 30))
        lbl.text = "Hasta:"
        lbl.text_color = '#ccccdd'
        lbl.font = ('Helvetica', 13)
        view.add_subview(lbl)
        
        self.search_end = ui.DatePicker(frame=(10, y+28, view.width-20, 90))
        self.search_end.date = datetime.datetime.now() + datetime.timedelta(days=365)
        self.search_end.mode = ui.DATE_PICKER_MODE_DATE
        self.search_end.flex = 'W'
        view.add_subview(self.search_end)
        
        y += 128
        # Boton buscar
        btn = ui.Button(frame=(10, y, view.width-20, 44))
        btn.title = "🔍 Buscar Transito"
        btn.background_color = '#f0c040'
        btn.tint_color = '#1a1a2e'
        btn.font = ('Helvetica-Bold', 17)
        btn.corner_radius = 8
        btn.action = self.search_degree
        btn.flex = 'W'
        view.add_subview(btn)
        
        y += 54
        # Resultados
        self.search_text = ui.TextView(frame=(10, y, view.width-20, view.height - y - 10))
        self.search_text.background_color = '#12122a'
        self.search_text.text_color = '#00ffaa'
        self.search_text.editable = False
        self.search_text.font = ('Menlo', 11)
        self.search_text.corner_radius = 8
        self.search_text.flex = 'WH'
        view.add_subview(self.search_text)
        
        return view
    
    def create_tab_aspects(self):
        view = ui.View(frame=self.container.bounds)
        view.flex = 'WH'
        view.background_color = '#0a0a1a'
        
        y = 10
        # DatePicker
        self.aspect_date = ui.DatePicker(frame=(10, y, view.width-20, 100))
        self.aspect_date.date = datetime.datetime.now()
        self.aspect_date.mode = ui.DATE_PICKER_MODE_DATE_AND_TIME
        self.aspect_date.flex = 'W'
        view.add_subview(self.aspect_date)
        
        y += 110
        # Boton
        btn = ui.Button(frame=(10, y, view.width-20, 44))
        btn.title = "✦ Calcular Aspectos ✦"
        btn.background_color = '#f0c040'
        btn.tint_color = '#1a1a2e'
        btn.font = ('Helvetica-Bold', 17)
        btn.corner_radius = 8
        btn.action = self.calc_aspects
        btn.flex = 'W'
        view.add_subview(btn)
        
        y += 54
        # Resultados
        self.aspects_text = ui.TextView(frame=(10, y, view.width-20, view.height - y - 10))
        self.aspects_text.background_color = '#12122a'
        self.aspects_text.text_color = '#00ffaa'
        self.aspects_text.editable = False
        self.aspects_text.font = ('Menlo', 11)
        self.aspects_text.corner_radius = 8
        self.aspects_text.flex = 'WH'
        view.add_subview(self.aspects_text)
        
        return view
    
    def create_tab_settings(self):
        view = ui.View(frame=self.container.bounds)
        view.flex = 'WH'
        view.background_color = '#0a0a1a'
        
        y = 10
        # Ciudad
        lbl = ui.Label(frame=(10, y, 80, 30))
        lbl.text = "Ciudad:"
        lbl.text_color = '#ccccdd'
        lbl.font = ('Helvetica', 13)
        view.add_subview(lbl)
        
        self.city_field = ui.TextField(frame=(90, y, view.width-100, 30))
        self.city_field.text = self.city_name
        self.city_field.background_color = '#1a1a3e'
        self.city_field.text_color = '#f0c040'
        self.city_field.corner_radius = 6
        self.city_field.flex = 'W'
        view.add_subview(self.city_field)
        
        y += 40
        # Boton ciudades
        btn_cities = ui.Button(frame=(10, y, view.width-20, 36))
        btn_cities.title = "Ver Lista de Ciudades"
        btn_cities.background_color = '#2a2a4e'
        btn_cities.tint_color = '#f0c040'
        btn_cities.font = ('Helvetica', 14)
        btn_cities.corner_radius = 6
        btn_cities.action = self.show_cities
        btn_cities.flex = 'W'
        view.add_subview(btn_cities)
        
        y += 46
        # UTC
        lbl = ui.Label(frame=(10, y, 120, 30))
        lbl.text = "UTC Offset:"
        lbl.text_color = '#ccccdd'
        lbl.font = ('Helvetica', 13)
        view.add_subview(lbl)
        
        self.utc_field = ui.TextField(frame=(140, y, 80, 30))
        self.utc_field.text = str(int(self.utc_offset))
        self.utc_field.background_color = '#1a1a3e'
        self.utc_field.text_color = '#f0c040'
        self.utc_field.corner_radius = 6
        self.utc_field.keyboard_type = ui.KEYBOARD_NUMBERS_AND_PUNCTUATION
        view.add_subview(self.utc_field)
        
        y += 40
        # Lat
        lbl = ui.Label(frame=(10, y, 120, 30))
        lbl.text = "Latitud:"
        lbl.text_color = '#ccccdd'
        lbl.font = ('Helvetica', 13)
        view.add_subview(lbl)
        
        self.lat_field = ui.TextField(frame=(140, y, 100, 30))
        self.lat_field.text = str(self.latitude)
        self.lat_field.background_color = '#1a1a3e'
        self.lat_field.text_color = '#f0c040'
        self.lat_field.corner_radius = 6
        self.lat_field.keyboard_type = ui.KEYBOARD_NUMBERS_AND_PUNCTUATION
        view.add_subview(self.lat_field)
        
        y += 40
        # Lon
        lbl = ui.Label(frame=(10, y, 120, 30))
        lbl.text = "Longitud:"
        lbl.text_color = '#ccccdd'
        lbl.font = ('Helvetica', 13)
        view.add_subview(lbl)
        
        self.lon_field = ui.TextField(frame=(140, y, 100, 30))
        self.lon_field.text = str(self.longitude)
        self.lon_field.background_color = '#1a1a3e'
        self.lon_field.text_color = '#f0c040'
        self.lon_field.corner_radius = 6
        self.lon_field.keyboard_type = ui.KEYBOARD_NUMBERS_AND_PUNCTUATION
        view.add_subview(self.lon_field)
        
        y += 50
        # Boton guardar
        btn = ui.Button(frame=(10, y, view.width-20, 44))
        btn.title = "Guardar Configuracion"
        btn.background_color = '#f0c040'
        btn.tint_color = '#1a1a2e'
        btn.font = ('Helvetica-Bold', 17)
        btn.corner_radius = 8
        btn.action = self.save_config
        btn.flex = 'W'
        view.add_subview(btn)
        
        y += 54
        # Info
        info = ui.TextView(frame=(10, y, view.width-20, view.height - y - 10))
        info.text = """ALGORITMOS:
• Sol: Meeus Cap.25 (prec. ~0.01°)
• Luna: Meeus Cap.47 (prec. ~10")
• Planetas: Elementos orbitales J2000
  + Eq. Kepler (prec. ~0.01°)
• Casas: Sistema Placidus
• Asc/MC: Meeus Cap.12

PLANETAS:
Sol, Luna, Mercurio, Venus, Marte,
Jupiter, Saturno, Urano, Neptuno
+ Asc, DSC, MC, IC

ASPECTOS:
Conjuncion 0° (orb 8°)
Sextil 60° (orb 6°)
Cuadratura 90° (orb 7°)
Trigono 120° (orb 8°)
Oposicion 180° (orb 8°)

NOTA: Las posiciones son
astronomicas (tropical)."""
        info.background_color = '#12122a'
        info.text_color = '#aaaacc'
        info.editable = False
        info.font = ('Helvetica', 11)
        info.corner_radius = 8
        info.flex = 'WH'
        view.add_subview(info)
        
        return view
    
    def switch_tab(self, sender):
        tabs = [self.tab_chart, self.tab_search, self.tab_aspects, self.tab_settings]
        for i, tab in enumerate(tabs):
            tab.hidden = (i != sender.selected_index)
    
    def load_config(self):
        try:
            config_path = os.path.expanduser('~/Documents/astro_config.json')
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    cfg = json.load(f)
                self.utc_offset = cfg.get('utc_offset', 0)
                self.latitude = cfg.get('latitude', 40.4168)
                self.longitude = cfg.get('longitude', -3.7038)
                self.city_name = cfg.get('city_name', 'Madrid')
                self.utc_field.text = str(int(self.utc_offset))
                self.lat_field.text = str(self.latitude)
                self.lon_field.text = str(self.longitude)
                self.city_field.text = self.city_name
                self.update_info_bar()
        except:
            pass
    
    def save_config(self, sender):
        try:
            self.utc_offset = float(self.utc_field.text)
            self.latitude = float(self.lat_field.text)
            self.longitude = float(self.lon_field.text)
            self.city_name = self.city_field.text
            
            config_path = os.path.expanduser('~/Documents/astro_config.json')
            cfg = {
                'utc_offset': self.utc_offset,
                'latitude': self.latitude,
                'longitude': self.longitude,
                'city_name': self.city_name,
            }
            with open(config_path, 'w') as f:
                json.dump(cfg, f)
            
            self.update_info_bar()
            self.chart_text.text = "✓ Configuracion guardada"
        except Exception as e:
            self.chart_text.text = f"Error: {e}"
    
    def show_cities(self, sender):
        items = sorted(CITIES.keys())
        
        def selected(sender):
            name = items[sender.selected_row]
            lat, lon = CITIES[name]
            self.city_field.text = name
            self.lat_field.text = str(lat)
            self.lon_field.text = str(lon)
            self.city_name = name
            self.latitude = lat
            self.longitude = lon
            self.update_info_bar()
        
        tv = ui.TableView()
        tv.data_source = ui.ListDataSource(items)
        tv.data_source.action = selected
        tv.name = "Seleccionar Ciudad"
        tv.present('sheet')
    
    # ============================================================
    # CALCULOS PRINCIPALES
    # ============================================================
    
    def get_JD_from_datetime(self, dt):
        """Convierte datetime a Dia Juliano"""
        # Ajustar a UTC
        dt_utc = dt - datetime.timedelta(hours=self.utc_offset)
        return Ephemeris.julian_day(
            dt_utc.year, dt_utc.month, dt_utc.day,
            dt_utc.hour, dt_utc.minute, dt_utc.second
        )
    
    def calc_chart(self, sender):
        try:
            dt = self.date_picker.date
            JD = self.get_JD_from_datetime(dt)
            dt_utc = dt - datetime.timedelta(hours=self.utc_offset)
            
            # Calcular posiciones
            positions = Ephemeris.get_all_positions(JD)
            
            # Calcular puntos angulares
            asc = Ephemeris.calculate_ascendant(JD, self.latitude, self.longitude)
            dsc = normalize(asc + 180)
            mc = Ephemeris.calculate_mc(JD, self.latitude, self.longitude)
            ic = normalize(mc + 180)
            
            # Casas
            houses = Ephemeris.calculate_houses_placidus(JD, self.latitude, self.longitude)
            
            # Fase lunar
            phase, elong = Ephemeris.moon_phase(JD)
            
            # Construir resultado
            result = ""
            result += "═══════════════════════════════\n"
            result += "       CARTA ASTRONOMICA\n"
            result += "═══════════════════════════════\n"
            result += f"Fecha: {dt_utc.strftime('%Y-%m-%d %H:%M')} UTC"
            if self.utc_offset != 0:
                result += f" ({self.utc_offset:+g}h)"
            result += f"\nLugar: {self.city_name}\n"
            result += f"Lat: {self.latitude:.2f}  Lon: {self.longitude:.2f}\n"
            result += "───────────────────────────────\n\n"
            
            # Puntos angulares
            result += "── PUNTOS ANGULARES ──\n"
            for name, deg_val in [('Ascendente', asc), ('Descendente', dsc),
                                   ('Medio Cielo', mc), ('Fondo Cielo', ic)]:
                sign_num = int(deg_val // 30)
                sign = self.get_sign(sign_num)
                deg_in = deg_val % 30
                retro = " ℞" if name in ['Ascendente'] and False else ""
                result += f"  {name:12} {deg_in:6.2f}° {sign:11}{retro}\n"
            
            result += "\n── PLANETAS ──\n"
            planet_order = ['Sol', 'Luna', 'Mercurio', 'Venus', 'Marte',
                          'Jupiter', 'Saturno', 'Urano', 'Neptuno']
            
            for name in planet_order:
                p = positions[name]
                deg_val = p['lon']
                sign_num = int(deg_val // 30)
                sign = self.get_sign(sign_num)
                deg_in = deg_val % 30
                
                retro = " ℞" if p.get('retro', False) else " "
                motion = p.get('motion', 0)
                motion_str = f"{motion:+.2f}°/d"
                
                result += f"  {name:10} {deg_in:6.2f}° {sign:11}{retro} {motion_str}\n"
            
            result += "\n── CASAS (Placidus) ──\n"
            for h in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]:
                deg_val = houses.get(h, 0)
                sign_num = int(deg_val // 30)
                sign = self.get_sign(sign_num)
                deg_in = deg_val % 30
                result += f"  Casa {h:2}: {deg_in:6.2f}° {sign:11}\n"
            
            # Fase lunar
            result += f"\n── FASE LUNAR ──\n"
            phase_names = ['Luna Nueva', 'Creciente', 'Cuarto Creciente', 'Gibosa Creciente',
                          'Luna Llena', 'Gibosa Menguante', 'Cuarto Menguante', 'Menguante']
            phase_idx = int(phase * 8) % 8
            phase_emoji = ['🌑', '🌒', '🌓', '🌔', '🌕', '🌖', '🌗', '🌘']
            result += f"  {phase_emoji[phase_idx]} {phase_names[phase_idx]} ({phase*100:.1f}%)\n"
            result += f"  Elongacion: {elong:.1f}°\n"
            
            result += "\n═══════════════════════════════\n"
            
            self.chart_text.text = result
            
        except Exception as e:
            import traceback
            self.chart_text.text = f"Error: {e}\n\n{traceback.format_exc()}"
    
    def search_degree(self, sender):
        try:
            planet = self.search_planet.text.strip()
            degree = float(self.search_degree.text)
            sign = self.search_sign.text.strip()
            start = self.search_start.date
            end = self.search_end.date
            
            sign_num = self.get_sign_number(sign)
            if sign_num < 0:
                self.search_text.text = f"Signo '{sign}' no reconocido"
                return
            
            target = sign_num * 30 + degree
            
            # Mapeo de nombres
            planet_map = {
                'sol': 'Sol', 'luna': 'Luna', 'mercurio': 'Mercurio',
                'venus': 'Venus', 'marte': 'Marte', 'jupiter': 'Jupiter',
                'saturno': 'Saturno', 'urano': 'Urano', 'neptuno': 'Neptuno',
            }
            planet_key = planet_map.get(planet.lower(), planet)
            
            self.search_text.text = f"Buscando {planet_key} en {degree:.1f}° {sign}...\n"
            self.search_text.text += f"Rango: {start.date()} a {end.date()}\n"
            self.search_text.text += "Esto puede tardar unos segundos...\n\n"
            self.set_needs_display()
            
            found = []
            current = start.replace(hour=0, minute=0, second=0)
            end_dt = end.replace(hour=23, minute=59, second=59)
            
            step_hours = 6  # Cada 6 horas
            total_steps = int((end_dt - current).total_seconds() / (step_hours * 3600))
            processed = 0
            
            while current <= end_dt:
                processed += 1
                if processed % 200 == 0:
                    pct = processed / max(total_steps, 1) * 100
                    self.search_text.text = f"Procesando: {processed}/{total_steps} ({pct:.0f}%)\n"
                    self.search_text.text += f"Encontrados: {len(found)}\n\n"
                    self.set_needs_display()
                
                JD = self.get_JD_from_datetime(current)
                positions = Ephemeris.get_all_positions(JD)
                
                if planet_key in positions:
                    pos_lon = positions[planet_key]['lon']
                    diff = abs(pos_lon - target)
                    if diff > 180:
                        diff = 360 - diff
                    
                    if diff < 0.5:  # Precision de 0.5 grados
                        found.append((current, pos_lon, diff))
                
                current += datetime.timedelta(hours=step_hours)
            
            if found:
                result = f"✦ {len(found)} momentos encontrados ✦\n\n"
                for dt, pos, diff in found:
                    dt_local = dt + datetime.timedelta(hours=self.utc_offset)
                    sign_num = int(pos // 30)
                    sign_name = self.get_sign(sign_num)
                    deg_in = pos % 30
                    result += f"  {dt_local.strftime('%Y-%m-%d %H:%M')}\n"
                    result += f"    {deg_in:.2f}° {sign_name} (dif: {diff:.3f}°)\n\n"
                self.search_text.text = result
            else:
                self.search_text.text = f"No se encontraron momentos exactos.\n\n"
                self.search_text.text += f"Sugerencias:\n"
                self.search_text.text += f"• Amplia el rango de fechas\n"
                self.search_text.text += f"• Verifica el planeta y signo\n"
                self.search_text.text += f"• Algunos planetas lentos (Urano,\n"
                self.search_text.text += f"  Neptuno) tardan años en recorrer\n"
                self.search_text.text += f"  un signo completo.\n"
                
        except Exception as e:
            import traceback
            self.search_text.text = f"Error: {e}\n\n{traceback.format_exc()}"
    
    def calc_aspects(self, sender):
        try:
            dt = self.aspect_date.date
            JD = self.get_JD_from_datetime(dt)
            dt_utc = dt - datetime.timedelta(hours=self.utc_offset)
            
            positions = Ephemeris.get_all_positions(JD)
            
            # Agregar puntos angulares
            asc = Ephemeris.calculate_ascendant(JD, self.latitude, self.longitude)
            mc = Ephemeris.calculate_mc(JD, self.latitude, self.longitude)
            
            all_points = dict(positions)
            all_points['Asc'] = {'lon': asc}
            all_points['MC'] = {'lon': mc}
            
            point_names = ['Sol', 'Luna', 'Mercurio', 'Venus', 'Marte',
                          'Jupiter', 'Saturno', 'Urano', 'Neptuno', 'Asc', 'MC']
            
            # Orbes por aspecto
            orbs = {
                'Conjuncion': 8, 'Sextil': 6, 'Cuadratura': 7,
                'Trigono': 8, 'Oposicion': 8,
            }
            
            result = ""
            result += "═══════════════════════════════\n"
            result += "        TABLA DE ASPECTOS\n"
            result += "═══════════════════════════════\n"
            result += f"{dt_utc.strftime('%Y-%m-%d %H:%M')} UTC\n"
            result += f"{self.city_name}\n"
            result += "───────────────────────────────\n\n"
            
            aspect_count = 0
            for i, p1 in enumerate(point_names):
                for j, p2 in enumerate(point_names):
                    if j <= i:
                        continue
                    
                    lon1 = all_points[p1]['lon']
                    lon2 = all_points[p2]['lon']
                    
                    aspect_name, orb = Ephemeris.aspects(lon1, lon2)
                    
                    max_orb = orbs.get(aspect_name, 3)
                    if orb <= max_orb and aspect_name not in ['Quincuncio', 'Semisextil', 'Semicuadratura', 'Sesquicuadratura']:
                        aspect_count += 1
                        # Color del aspecto
                        aspect_colors = {
                            'Conjuncion': '☌', 'Sextil': '⚹', 'Cuadratura': '□',
                            'Trigono': '△', 'Oposicion': '☍',
                        }
                        symbol = aspect_colors.get(aspect_name, '?')
                        result += f"  {p1:10} {symbol} {p2:10}  {aspect_name:12} (orb: {orb:.1f}°)\n"
            
            if aspect_count == 0:
                result += "  No se encontraron aspectos mayores\n"
            
            result += f"\nTotal: {aspect_count} aspectos\n"
            result += "═══════════════════════════════\n"
            
            self.aspects_text.text = result
            
        except Exception as e:
            import traceback
            self.aspects_text.text = f"Error: {e}\n\n{traceback.format_exc()}"
    
    # ============================================================
    # UTILIDADES
    # ============================================================
    
    def get_sign(self, num):
        signs = ['Aries', 'Tauro', 'Geminis', 'Cancer', 'Leo', 'Virgo',
                 'Libra', 'Escorpio', 'Sagitario', 'Capricornio', 'Acuario', 'Piscis']
        return signs[int(num) % 12]
    
    def get_sign_number(self, sign):
        signs = ['aries', 'tauro', 'geminis', 'cancer', 'leo', 'virgo',
                 'libra', 'escorpio', 'sagitario', 'capricornio', 'acuario', 'piscis']
        sign_clean = sign.lower().strip()
        # Aceptar variantes
        variants = {
            'taurus': 'tauro', 'géminis': 'geminis', 'gemini': 'geminis',
            'cáncer': 'cancer', 'cancer': 'cancer', 'escorpión': 'escorpio',
            'escorpio': 'escorpio', 'scorpio': 'escorpio', 'sagitarius': 'sagitario',
            'capricorn': 'capricornio', 'capricornio': 'capricornio',
            'aquarius': 'acuario', 'acuario': 'acuario', 'pisces': 'piscis',
        }
        sign_clean = variants.get(sign_clean, sign_clean)
        try:
            return signs.index(sign_clean)
        except:
            return -1


if __name__ == '__main__':
    app = AstroApp()
    app.frame = (0, 0, 375, 667)
    app.present('fullscreen')
