// Retire only the former public quote PWA; leave other apps untouched.
self.addEventListener('install',()=>self.skipWaiting());
self.addEventListener('activate',event=>event.waitUntil((async()=>{
  await caches.delete('daham-app-v3');
  await self.registration.unregister();
  const clients=await self.clients.matchAll({type:'window'});
  await Promise.all(clients.filter(client=>client.url.startsWith(self.registration.scope)).map(client=>client.navigate(client.url)));
})()));
