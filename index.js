import { Client, Events, GatewayIntentBits } from 'discord.js';
import 'dotenv/config';

const client = new Client({ intents: GatewayIntentBits.Guilds });

client.on(Events.ClientReady, client => {
    console.log(`Logged in as ${client.user.tag}`);
});

client.login(process.env.DEV_TOKEN);