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

status_label = "<h3>{msg}</h3>"

header_timestamp = u"<h3 style='color:grey'>{dt:%I}:{dt:%M}:{dt:%S}{dt:%p}</h3>"

header_datestamp = u"<h3 style='color:grey'>{dt.month}-{dt.day}-{dt.year}</h3>"

header_sender = u"<h3 style='color:{color}'>{host_name}</h3>"

not_connected_msg = u"You are not connected! Check your account info."

disconnected_msg = u"Got disconnected! Check your internet connection."

is_in_clipboard_label = u"<h5 style='color:DarkOrchid'>In your clipboard!</h5>"

about_info = """
<h1>PasteBeam</h1>
<h5 style='color:grey'>1.0.0</h5>
<p>Designed in New York City with love.</p>
"""

about_copy_right = "<b>&copy; {org}</b>"
about_device_id = "<span style='color:grey'>Device ID: {id}</span>"
about_url = "<a href='{url}'>{title}</a>"