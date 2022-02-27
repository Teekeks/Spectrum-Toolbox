import logging

from distee.application_command import ApplicationCommand, ApplicationCommandOption
from distee.client import Client
from distee.components import ActionRow, Button, Modal, TextInput
from distee.enums import TextInputType, ButtonStyle, Event, ApplicationCommandOptionType, ApplicationCommandType
from distee.flags import Intents, Permissions
from distee.guild import Member, Guild
from distee.interaction import Interaction
import json
import os.path

with open('config.json') as conf_file:
    cfg = json.load(conf_file)

logging.basicConfig(level=logging.INFO)

client = Client()
client.build_user_cache = False
client.build_member_cache = False
intents = Intents().set(['GUILDS'])

colors = [
    0x434B4D,
    0xB32821,
    0xC6A664,
    0x781F19,
    0xBEBD7F,
    0xA2231D,
    0x343E40,
    0xD84B20,
    0xFFA420,
    0x287233
]

c_success = 0x287233
c_fail = 0xA2231D

S_UNKNOWN = 0
S_AVAILABLE = 1
S_PING = 2
S_EMERGENCY = 3
S_UNAVAILABLE = 4

EMOTES = [
    '<:point_blue:917097809642135552>',
    '<:point_green:917097855372623993>',
    '<:point_yellow:947531355418427422>',
    '<:point_red:917098020871503943>',
    '<:point_grey:917097712225222666>'
]


usr_states = {}
ch_id = None
msg_id = None


def load():
    if os.path.isfile('storage.json'):
        with open('storage.json', 'r') as fi:
            dat = json.load(fi)
        global usr_states, ch_id, msg_id
        usr_states = dat['usr_states']
        ch_id = dat.get('ch_id')
        msg_id = dat.get('msg_id')
        # FIXME implement


def safe():
    dat = {
        'usr_states': usr_states,
        'ch_id': ch_id,
        'msg_id': msg_id
    }
    with open('storage.json', 'w') as fi:
        json.dump(dat, fi)


async def set_available(inter: Interaction, av: int):
    global usr_states
    if str(inter.member.id) not in usr_states.keys():
        await inter.send('You are not on the list!', ephemeral=True)
        return
    usr_states[str(inter.member.id)] = av
    await inter.defer_message_edit()
    await refresh_msg(inter.member.guild)


@client.interaction_handler('btn_av_available')
async def set_av(inter: Interaction):
    await set_available(inter, S_AVAILABLE)


@client.interaction_handler('btn_av_ping')
async def set_av(inter: Interaction):
    await set_available(inter, S_PING)


@client.interaction_handler('btn_av_emergency')
async def set_av(inter: Interaction):
    await set_available(inter, S_EMERGENCY)


@client.interaction_handler('btn_av_unavailable')
async def set_av(inter: Interaction):
    await set_available(inter, S_UNAVAILABLE)


async def refresh_msg(guild: Guild):
    global ch_id
    if ch_id is None:
        return
    content = ''
    for uid, av in usr_states.items():
        content += f'{EMOTES[av]}| <@{uid}>\n'
    content += '\n-----------------------------------\n\n' \
               f'Select {EMOTES[S_AVAILABLE]} if you are active and available\n' \
               f'Select {EMOTES[S_PING]} if you are only available via ping\n' \
               f'Select {EMOTES[S_EMERGENCY]} if you are only available for emergencies\n' \
               f'Select {EMOTES[S_UNAVAILABLE]} if you are not available\n' \
               f'{EMOTES[S_UNKNOWN]} means nothing was set yet'
    comps = [ActionRow([
        Button(
            'btn_av_available',
            label='Active',
            style=ButtonStyle.SECONDARY,
            emoji={'id': 917097855372623993}
        ),
        Button(
            'btn_av_ping',
            label='Ping only',
            style=ButtonStyle.SECONDARY,
            emoji={'id': 947531355418427422}
        ),
        Button(
            'btn_av_emergency',
            label='Emergency only',
            style=ButtonStyle.SECONDARY,
            emoji={'id': 917098020871503943}
        ),
        Button(
            'btn_av_unavailable',
            label='Unavailable',
            style=ButtonStyle.SECONDARY,
            emoji={'id': 917097712225222666}
        )
    ])]
    global msg_id
    ch = guild.get_channel(ch_id)

    if msg_id is not None:
        await ch.edit_message(msg_id, embeds=[{
            'title': 'Team availability',
            'description': content
        }], components=comps)
    else:
        msg = await ch.send(embeds=[{
            'title': 'Team availability',
            'description': content
        }], components=comps)
        msg_id = msg.id

    pass


async def available_command(inter: Interaction):
    op = inter.data.options[0]['name']
    global usr_states
    if op == 'add':
        usr = int(inter.data.options[0]['options'][0]['value'])
        if str(usr) in usr_states.keys():
            await inter.send('User is already on the list!', ephemeral=True)
            return
        usr_states[str(usr)] = S_UNKNOWN
        await refresh_msg(inter.member.guild)
        await inter.send('User was added to the list!', ephemeral=True)
        return
    elif op == 'remove':
        usr = int(inter.data.options[0]['options'][0]['value'])
        if str(usr) not in usr_states.keys():
            await inter.send('User is not on the list!', ephemeral=True)
            return
        usr_states.pop(usr, None)
        await refresh_msg(inter.member.guild)
        await inter.send('User was removed from the list!', ephemeral=True)
    elif op == 'post':
        ch = inter.member.guild.get_channel(inter.channel_id)
        global ch_id, msg_id
        ch_id = ch.id
        msg_id = None
        await refresh_msg(inter.member.guild)
        await inter.send('List was posted!', ephemeral=True)


rm_cache = {}


@client.interaction_handler('raw_message_modal')
async def raw_message_modal(inter: Interaction):
    await inter.defer_send(ephemeral=True)
    ch = rm_cache[inter.member.id]
    channel = inter.member.guild.get_channel(ch)
    data = json.loads(inter.data.components['value']['value'])
    embed = data.get('embed')
    content = data.get('content')
    components = data.get('components')
    await channel.send(content=content, embeds=[embed], components=components)
    await inter.send_followup(f'Message was send to <#{channel.id}>', ephemeral=True)


async def send_raw_message_command(inter: Interaction):
    global rm_cache
    ch = int(inter.data.options[0]['value'])
    rm_cache[inter.member.id] = ch
    await inter.send_modal(Modal(
        'raw_message_modal',
        'Send a raw message',
        components=[
            ActionRow([
                TextInput(
                    'value',
                    'Paste json here',
                    TextInputType.PARAGRAPH
                )
            ])
        ]
    ))


@client.event(Event.GUILD_JOINED)
async def on_guild_joined(guild: Guild):
    ac = client.get_application_commands('available', ApplicationCommandType.CHAT_INPUT)
    roles = [{
        'id': guild.owner_id.id,
        'type': 2,
        'permission': True
    }]
    for role in guild.roles.values():
        if Permissions.ADMINISTRATOR in role.permissions:
            roles.append({
                'id': role.id,
                'type': 1,
                'permission': True
            })
    await ac.set_permissions(guild.id, roles)
    ac = client.get_application_commands('send-raw-message', ApplicationCommandType.CHAT_INPUT)
    await ac.set_permissions(guild.id, roles)


ap = ApplicationCommand(name='available',
                        default_permission=False,
                        default_member_permissions=8,
                        dm_permission=False,
                        description='Available Mods Manager',
                        options=[
                            ApplicationCommandOption(
                                name='add',
                                type=ApplicationCommandOptionType.SUB_COMMAND,
                                description='Add a user to the list',
                                options=[
                                    ApplicationCommandOption(
                                        name='user',
                                        required=True,
                                        description='the user to add',
                                        type=ApplicationCommandOptionType.USER
                                    )
                                ]
                            ),
                            ApplicationCommandOption(
                                name='remove',
                                type=ApplicationCommandOptionType.SUB_COMMAND,
                                description='Remove a user from the list',
                                options=[
                                    ApplicationCommandOption(
                                        name='user',
                                        required=True,
                                        description='the user to remove',
                                        type=ApplicationCommandOptionType.USER
                                    )
                                ]
                            ),
                            ApplicationCommandOption(
                                name='post',
                                type=ApplicationCommandOptionType.SUB_COMMAND,
                                description='Post the list to the current channel'
                            )
                        ])
client.register_command(ap, available_command, True, None)

ap = ApplicationCommand(name='send-raw-message',
                        description='Send a message to a channel, may include embeds',
                        default_permission=False,
                        default_member_permissions=8,
                        dm_permission=False,
                        options=[
                            ApplicationCommandOption(
                                name='channel',
                                description='The channel the message should be send to',
                                type=ApplicationCommandOptionType.CHANNEL,
                                required=True
                            )
                        ])
client.register_command(ap, send_raw_message_command, True, None)

load()

try:
    client.run(cfg['token'], intents=intents)
finally:
    safe()
