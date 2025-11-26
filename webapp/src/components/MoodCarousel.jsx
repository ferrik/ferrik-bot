import React from 'react';
import { Swiper, SwiperSlide } from 'swiper/react';
import 'swiper/css';

const MOODS = [
  { id: 'calm', emoji: '😌', title: 'Спокійний вечір', desc: 'Легка їжа для розслаблення' },
  { id: 'energy', emoji: '⚡', title: 'Енергія!', desc: 'Поживні страви для сили' },
  { id: 'party', emoji: '🥳', title: 'Party Time', desc: 'Сети для компанії' },
  { id: 'romantic', emoji: '❤️', title: 'Романтика', desc: 'Особливий вечір удвох' },
  { id: 'movie', emoji: '🧊', title: 'Кіно + перекус', desc: 'Снеки та напої' },
  { id: 'spicy', emoji: '🔥', title: 'Very Spicy', desc: 'Гостренького!' }
];

export default function MoodCarousel({ onSelect }) {
  return (
    <div className="mood-carousel">
      <h2>🎭 Який у тебе настрій?</h2>
      <Swiper
        spaceBetween={16}
        slidesPerView={2.5}
        className="mood-swiper"
      >
        {MOODS.map(mood => (
          <SwiperSlide key={mood.id}>
            <div 
              className="mood-card"
              onClick={() => onSelect(mood.id)}
            >
              <div className="mood-emoji">{mood.emoji}</div>
              <h3>{mood.title}</h3>
              <p>{mood.desc}</p>
            </div>
          </SwiperSlide>
        ))}
      </Swiper>
    </div>
  );
}
