image_preview = u"""<i style="color:grey">
<table>
    <tr>
        <td>
            <img src="data:image/png;base64,{b64}">
        </td>
        <td><table>
            <tr>
                <td>
                    {w} x {h} Pixels
                </td>
            </tr>
            <tr>
                <td>
                    {mp} Megapixels
                </td>
            </tr>
            <tr>
                <td>
                    {mb} Megabytes
                </td>
            </tr>
        </table></td>
    </tr>
</table>
</i>"""

corner_label_note = u"<i>%s</i>"
corner_label_type = u"<i style='color:grey;'>%s</i>"

icon_html = u"<img src='images/{name}.png' width={side} height={side}>"
