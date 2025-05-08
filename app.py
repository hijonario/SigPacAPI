from flask import Flask, request, jsonify
import requests
import xml.etree.ElementTree as ET

app = Flask(__name__)

@app.route('/parcela_catastro', methods=['GET'])
def parcela_catastro():
    try:
        x_utm = request.args.get('x', '467443')
        y_utm = request.args.get('y', '4426181')

        # Consultar referencia catastral por coordenadas
        url_coordenadas = f"https://ovc.catastro.meh.es/ovcservweb/OVCSWLocalizacionRC/OVCCoordenadas.asmx/Consulta_RCCOOR?SRS=EPSG:25830&Coordenada_X={x_utm}&Coordenada_Y={y_utm}"
        response_coord = requests.get(url_coordenadas)
        tree_coord = ET.fromstring(response_coord.content)

        ns = {'ns': 'http://www.catastro.meh.es/'}

        coord_node = tree_coord.find('.//ns:coord', ns)
        if coord_node is None:
            return jsonify({'error': 'No se encontró parcela en estas coordenadas'}), 404

        pc1 = coord_node.find('ns:pc/ns:pc1', ns).text
        pc2 = coord_node.find('ns:pc/ns:pc2', ns).text
        ref_catastral = pc1 + pc2

        ldt = coord_node.find('ns:ldt', ns).text
        descripcion = ldt
        provincia = "No disponible"
        municipio = "No disponible"
        if ldt:
            parts = ldt.split('(')
            if len(parts) == 2:
                municipio = parts[0].split('.')[-1].strip()
                provincia = parts[1].replace(')', '')

        # Consultar detalles de la parcela por referencia catastral
        url_parcela = f"https://ovc.catastro.meh.es/ovcservweb/OVCSWLocalizacionRC/OVCCallejero.asmx/Consulta_DNPRC?Provincia=&Municipio=&RC={ref_catastral}"
        response_parcela = requests.get(url_parcela)
        tree_parcela = ET.fromstring(response_parcela.content)

        superficie_total = 0
        sprs = tree_parcela.findall('.//ns:lspr/ns:spr', ns)

        if sprs:
            for spr in sprs:
                ssp = spr.find('ns:dspr/ns:ssp', ns)
                if ssp is not None and ssp.text:
                    superficie_total += float(ssp.text)
        else:
            ssp = tree_parcela.find('.//ns:lspr/ns:spr/ns:dspr/ns:ssp', ns)
            if ssp is not None and ssp.text:
                superficie_total = float(ssp.text)

        cpp = tree_parcela.find('.//ns:cpp', ns)
        poligono = parcela = 0
        if cpp is not None:
            cpa = cpp.find('ns:cpa', ns)
            cpo = cpp.find('ns:cpo', ns)
            poligono = float(cpa.text) if cpa is not None else 0
            parcela = float(cpo.text) if cpo is not None else 0

        return jsonify({
            'provincia': provincia,
            'municipio': municipio,
            'poligono': poligono,
            'parcela': parcela,
            'superficie_ha': superficie_total,
            'referencia_catastral': ref_catastral,
            'descripcion': descripcion
        })

    except Exception as e:
        return jsonify({
            'error': 'Error al procesar la solicitud',
            'detalle': str(e)
        }), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)





